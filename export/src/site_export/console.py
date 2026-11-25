"""Console replay data: run folder + check rows -> scenario document, clip document."""

from pathlib import Path

from site_export.runs import STAGES, Frame, read_events, read_frames, read_json, read_yaml


def scenario(scenario_id: str, run: Path, course: Path, checks: list[dict], fps: int) -> dict:
    frames = read_frames(run)
    manifest = read_json(run / 'manifest.json')
    run_config = read_yaml(run / 'run_config.yaml')

    tracks: dict[int, list[list]] = {}
    frozen_events, dropped = set(), []
    for e in read_events(run):
        if e['status'] == 'frame_dropped':
            # the contract gives only the expected time; t is rounded to 3 digits, so t * fps is within 0.015 of the frame
            frame = round(e['t'] * fps)
            if abs(e['t'] * fps - frame) > 0.05:
                raise ValueError(f'{run}: frame_dropped at t {e["t"]} is not on a frame of {fps} fps')
            dropped.append({'frame': frame, 't': e['t']})
        elif e['status'] == 'frozen':
            frozen_events.add(e['frame'])
        else:
            tracks.setdefault(e['frame'], []).append(
                [e['track_id'], e['cls'], round(e['score'], 3), *(round(v, 2) for v in e['xyxy'])])

    processed = {f.frame for f in frames}
    if not tracks.keys() <= processed:
        raise ValueError(f'{run}: ok events on frames missing from frames.csv: {sorted(tracks.keys() - processed)}')
    frozen_rows = {f.frame for f in frames if f.status == 'frozen'}
    if frozen_events != frozen_rows:
        raise ValueError(f'{run}: frozen events {sorted(frozen_events)} != frozen rows of frames.csv {sorted(frozen_rows)}')

    doc = {
        'id': scenario_id,
        'run': run.relative_to(course).as_posix(),
        'engine': engine(run_config),
        'scenario': manifest['scenario'],
        'frozen_check': manifest.get('frozen_check'),
        'stages': list(STAGES),
        'frames': [frame_doc(f, tracks.get(f.frame, []), fps) for f in frames],
        'dropped': dropped,
        'summary': read_json(run / 'summary.json'),
        'checks': checks,
    }
    verify_counts(doc)
    return doc


def frame_doc(f: Frame, tracks: list[list], fps: int) -> dict:
    return {'frame': f.frame, 't': round(f.frame / fps, 3), 'status': f.status, 'ms': list(f.ms),
            'n_tracks': f.n_tracks, 'frame_diff': f.frame_diff, 'tracks': tracks}


def engine(run_config: dict) -> dict:
    cfg = run_config['config']
    return {
        'weights': cfg['model']['weights'],
        'device': str(cfg['inference']['device']),
        'cpu': run_config['hardware']['cpu'],
        'gpu': run_config['hardware'].get('gpu'),  # older runs record no gpu key
        'versions': run_config['versions'],
    }


def verify_counts(doc: dict) -> None:
    # the console shows what the events say; it must agree with the numbers of the scenario table
    frames = doc['frames']
    ok_at = {f['frame']: len(f['tracks']) for f in frames}
    dropped = {d['frame'] for d in doc['dropped']}
    for c in doc['checks']:
        if c['check'] == 'frozen':
            got = sum(f['status'] == 'frozen' for f in frames)
        elif c['check'] == 'frame_dropped':
            got = len(doc['dropped'])
        elif c['check'] == 'ok_at_dropped':
            got = sum(ok_at.get(f, 0) for f in dropped)
        elif c['check'] == 'ok_in_freeze':
            lo, hi = c['detail']['freeze_frames']
            got = sum(n for f, n in ok_at.items() if lo <= f <= hi)
        else:
            continue
        if got != c['ms']:
            raise ValueError(f'{doc["id"]}: {c["check"]} from events is {got}, results.json has {c["ms"]}')


def clip(clip_id: str, run_config: dict, contract: dict, classes: dict[int, str], size: tuple[int, int],
         media: dict[str, str]) -> dict:
    c = run_config['config']['clips'][clip_id]
    tracks = contract['cv_component']['outputs']['tracks']
    return {
        'id': clip_id,
        'name': c['name'],
        'fps': c['fps_src'],
        'frames': c['nb_frames'],
        'source_size': c['resolution'],
        'video_size': list(size),
        'vid_stride': run_config['config']['run']['vid_stride'],
        'contract': {
            'version': contract['cv_component']['contract_version'],
            'statuses': tracks['status'],
            'frame_budget_ms': tracks['frame_budget_ms'],
            'latency_p95_ms': tracks['latency_p95_ms'],
        },
        'classes': {str(k): v for k, v in sorted(classes.items())},
        'media': media,
    }
