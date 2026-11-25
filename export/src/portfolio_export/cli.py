"""Command line interface: python -m portfolio_export [--config config.yaml]."""

import argparse
from pathlib import Path

from portfolio_export import console, gt, media
from portfolio_export.config import Config, load_config
from portfolio_export.facts import facts
from portfolio_export.manifest import course_git, entry
from portfolio_export.outputs import sha256, write_json
from portfolio_export.recipe import write_recipe
from portfolio_export.runs import RUN_FILES, check_rows, read_json, read_yaml


def main() -> None:
    parser = argparse.ArgumentParser(prog='portfolio_export')
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

    for c in cfg.console:
        out = cfg.data_dir / 'console' / f'{c.id}.json'
        write_json(out, console.scenario(c.id, c.run, cfg.course, check_rows(c.results, c.row), fps))
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

    to_model, names = gt.class_map(cfg.eval_classes)
    clip_doc = console.clip(cfg.clip.id, run_config, read_yaml(cfg.contract), names, cfg.clip.size, {
        'video': clip_mp4.relative_to(public).as_posix(),
        'poster': still_files[str(cfg.clip.poster_frame)],
        'stills': still_files,
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
    done(out, [f.results for f in cfg.facts])

    for f in write_recipe(cfg.recipe):
        print(f'{(cfg.recipe.out / f).relative_to(cfg.site.parent)}')

    out = cfg.data_dir / 'manifest.json'
    write_json(out, {'course': course_git(cfg.course), 'files': files}, compact=False)
    print(f'{out.relative_to(cfg.site.parent)}')
