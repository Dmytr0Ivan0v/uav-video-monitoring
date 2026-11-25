"""Command line interface: python -m site_export [--config config.yaml]."""

import argparse
from pathlib import Path

from site_export import console, gt, media
from site_export.change import export_change
from site_export.config import Config, load_config
from site_export.engineering import engineering
from site_export.facts import facts
from site_export.hero import hero_clip
from site_export.manifest import course_git, entry
from site_export.model import export_model
from site_export.outputs import sha256, write_json
from site_export.recipe import write_recipe
from site_export.runs import RUN_FILES, check_rows, read_json, read_yaml
from site_export.vo import Thumbs, run_doc


def main() -> None:
    parser = argparse.ArgumentParser(prog='site_export')
    parser.add_argument('--config', type=Path, default=Path('config.yaml'))
    args = parser.parse_args()
    export(load_config(args.config))


def export(cfg: Config) -> None:
    public = cfg.site / 'public'
    files: dict[str, dict] = {}

    def done(out: Path, sources: list[Path]) -> None:
        files[out.relative_to(public).as_posix()] = entry(out, sources, cfg.course)
        print(f'{out.relative_to(cfg.site.parent)}')

    run_config = read_yaml(cfg.console[0].run / 'run_config.yaml')
    clip_cfg = run_config['config']['clips'][cfg.clip.id]
    video = cfg.course / clip_cfg['video']
    video_sha = sha256(video)
    for c in cfg.console:
        used = read_json(c.run / 'manifest.json')['clip_sha256']
        if used != video_sha:
            raise ValueError(f'{c.run}: ran on a clip with sha256 {used}, {video} has {video_sha}')
    if media.frame_count(video) != clip_cfg['nb_frames']:
        raise ValueError(f'{video}: frame count differs from nb_frames {clip_cfg["nb_frames"]} of the run config')
    fps = clip_cfg['fps_src']

    runs = {}
    for c in cfg.console:
        out = cfg.data_dir / 'console' / f'{c.id}.json'
        runs[c.id] = console.scenario(c.id, c.run, cfg.course, check_rows(c.results, c.row), fps)
        write_json(out, runs[c.id])
        done(out, [c.run / f for f in RUN_FILES] + [c.results])

    # media: the clip, its poster and the picture every freeze scenario repeats
    name = f'clip{cfg.clip.id}'
    media_dir = cfg.media_dir / 'visdrone'
    clip_mp4 = media_dir / f'{name}.mp4'
    media.encode_clip(video, clip_mp4, cfg.clip.size, cfg.clip.crf, cfg.clip.gop)
    done(clip_mp4, [video])
    stills = {cfg.clip.poster_frame}
    for c in cfg.console:
        freeze = read_json(c.run / 'manifest.json')['scenario'].get('freeze')
        if freeze:
            stills.add(freeze['start_frame'])
    still_files = {}
    for frame in sorted(stills):
        out = media_dir / f'{name}_f{frame:03d}.jpg'
        media.still(video, out, frame, cfg.clip.size)
        still_files[str(frame)] = out.relative_to(public).as_posix()
        done(out, [video])

    hero_mp4 = media_dir / f'hero{cfg.clip.id}.mp4'
    hero_poster = media_dir / f'hero{cfg.clip.id}.webp'
    hero_run = next(c for c in cfg.console if c.id == cfg.hero.run)
    hero_clip(video, hero_mp4, hero_poster, runs[cfg.hero.run], clip_cfg['resolution'], cfg.clip.size, fps,
              cfg.hero.colors, cfg.hero.crf)
    for out in (hero_mp4, hero_poster):
        done(out, [video, hero_run.run / 'events.jsonl', hero_run.run / 'frames.csv'])

    for out, sources in export_model(cfg, video):
        done(out, sources)

    to_model, names = gt.class_map(cfg.eval_classes)
    clip_doc = console.clip(cfg.clip.id, run_config, read_yaml(cfg.contract), names, cfg.clip.size, {
        'video': clip_mp4.relative_to(public).as_posix(),
        'poster': still_files[str(cfg.clip.poster_frame)],
        'stills': still_files,
        'hero': hero_mp4.relative_to(public).as_posix(),
        'hero_poster': hero_poster.relative_to(public).as_posix(),
    })
    out = cfg.data_dir / 'console' / f'{name}.json'
    write_json(out, clip_doc, compact=False)
    done(out, [cfg.console[0].run / 'run_config.yaml', cfg.contract, cfg.eval_classes])

    annotations = cfg.course / run_config['config']['dataset_root'] / clip_cfg['gt']
    out = cfg.data_dir / 'visdrone' / f'{name}_gt.json'
    write_json(out, {'clip': cfg.clip.id, 'frames': gt.read_gt(annotations, to_model)})
    done(out, [annotations, cfg.eval_classes])

    out = cfg.data_dir / 'facts.json'
    write_json(out, facts(cfg.facts, cfg.course), compact=False)
    done(out, [f.file for f in cfg.facts])

    nav = cfg.navigation
    thumbs = Thumbs(every=nav.thumbs_every, size=nav.thumbs_size, cols=nav.thumbs_cols)
    vo_runs, shared = {}, None
    for name, run in nav.runs.items():
        out = cfg.media_dir / 'tum' / f'{name}.jpg'
        doc, sh = run_doc(run, cfg.course, out, public, thumbs)
        if shared is not None and sh['gt'] != shared['gt']:
            raise ValueError(f'{run}: associates other ground truth poses than the first run')
        shared = sh
        vo_runs[name] = doc
        seq = cfg.course / read_yaml(run / 'run_config.yaml')['sequence_dir']
        done(out, [seq / 'rgb.txt', run / 'run_config.yaml'])
    out = cfg.data_dir / 'navigation.json'
    write_json(out, {**shared, 'runs': vo_runs})
    gt_file = seq / read_yaml(run / 'run_config.yaml')['config']['sequence']['gt']
    done(out, [gt_file] + [run / f for run in nav.runs.values()
                           for f in ('trajectory.tum', 'vo_log.csv', 'eval.json', 'run_config.yaml', 'calibration.yaml')])

    for out, sources in export_change(cfg.change, cfg.course, cfg.data_dir, cfg.media_dir):
        done(out, sources)

    out = cfg.data_dir / 'engineering.json'
    doc, sources = engineering(cfg.engineering, cfg.course)
    write_json(out, doc, compact=False)
    done(out, sources)

    for f in write_recipe(cfg.recipe):
        print(f'{(cfg.recipe.out / f).relative_to(cfg.site.parent)}')

    out = cfg.data_dir / 'manifest.json'
    write_json(out, {'course': course_git(cfg.course), 'files': files}, compact=False)
    print(f'{out.relative_to(cfg.site.parent)}')
