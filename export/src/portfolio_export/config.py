"""Export configuration: config.yaml -> Config."""

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class Clip:
    id: str                 # clip key in the run configs, e.g. '137'
    size: tuple[int, int]   # site video width, height, px
    crf: int                # libx264 quality
    gop: int                # keyframe interval, frames
    poster_frame: int       # source frame, 0-based


@dataclass(frozen=True)
class ConsoleRun:
    id: str                 # scenario id on the site, file name of its JSON
    run: Path               # run folder, absolute
    results: Path           # results.json with the checks of this run, absolute
    row: str                # row name in that results.json


@dataclass(frozen=True)
class Fact:
    name: str
    results: Path           # results.json, absolute
    row: str
    check: str
    field: str              # key of the check row, dots go into nested dicts


@dataclass(frozen=True)
class Recipe:
    out: Path               # export/recipe, absolute
    train_args: Path        # Ultralytics args.yaml of the fine-tune, absolute
    onnx_export: Path       # export.json of the ONNX export run, absolute
    train_paths: dict[str, str]  # args.yaml key -> path inside cv_course


@dataclass(frozen=True)
class Config:
    course: Path            # cv_course checkout, absolute
    site: Path              # Astro project root, absolute
    contract: Path
    eval_classes: Path
    clip: Clip
    console: tuple[ConsoleRun, ...]
    facts: tuple[Fact, ...]
    recipe: Recipe

    @property
    def data_dir(self) -> Path:
        return self.site / 'public' / 'data'

    @property
    def media_dir(self) -> Path:
        return self.site / 'public' / 'media'


def load_config(path: Path) -> Config:
    with path.open(encoding='utf-8') as f:
        d = yaml.safe_load(f)
    base = path.resolve().parent
    course = (base / d['course']).resolve()
    site = (base / d['site']).resolve()
    # runs/ and the package are what every later step reads; a wrong path should fail here
    for need in (course / 'runs', course / 'src' / 'uav_monitor'):
        if not need.is_dir():
            raise FileNotFoundError(f'course: {course} is not a cv_course checkout, missing {need}')
    if not (site / 'astro.config.mjs').is_file():
        raise FileNotFoundError(f'site: {site} has no astro.config.mjs')

    c, r = d['clip'], d['recipe']
    return Config(
        course=course,
        site=site,
        contract=course / d['contract'],
        eval_classes=course / d['eval_classes'],
        clip=Clip(id=str(c['id']), size=tuple(c['size']), crf=c['crf'], gop=c['gop'],
                  poster_frame=c['poster_frame']),
        console=tuple(ConsoleRun(id=e['id'], run=course / e['run'], results=course / e['results'],
                                 row=e['row'])
                      for e in d['console']),
        facts=tuple(Fact(name=name, results=course / e['results'], row=e['row'], check=e['check'],
                         field=e['field'])
                    for name, e in d['facts'].items()),
        recipe=Recipe(out=base / r['out'], train_args=course / r['train_args'],
                      onnx_export=course / r['onnx_export'], train_paths=dict(r['train_paths'])),
    )
