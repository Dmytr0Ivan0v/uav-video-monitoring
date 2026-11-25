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
    file: Path              # JSON, YAML or CSV of the course, absolute
    match: dict | None      # pick the one row whose keys equal these values
    list: str               # key of the row list in a JSON document
    field: str              # dots go into nested dicts


@dataclass(frozen=True)
class Engine:
    id: str                 # console run id of the same engine
    bench: Path             # bench run folder, absolute
    results: Path           # quality results.json, absolute
    row: str


@dataclass(frozen=True)
class Engineering:
    engines: tuple[Engine, ...]
    scenarios: Path         # results.json of the stream scenarios
    stability: Path         # stability.json of the long run


@dataclass(frozen=True)
class Hero:
    run: str                # console run whose boxes are drawn into the clip
    crf: int
    colors: dict[int, str]  # model class id -> box colour, the site legend colours


@dataclass(frozen=True)
class Detector:
    onnx_export: Path       # export.json of the FP32 ONNX run, absolute
    deploy: Path            # deploy.yaml: input shape, consistency protocol and limits
    browser_limits: dict[str, str]  # browser backend -> key of consistency.max_score_diff in deploy.yaml
    reference_frames: tuple[int, ...]  # clip frames the browser is checked on
    fixture_min_score: float  # decode fixture keeps anchors with a best score at least this
    degradations: Path      # degradations.yaml of the robustness homework
    curves: Path            # curves.json of the robustness homework
    fixtures: Path          # site test fixtures, absolute


@dataclass(frozen=True)
class Navigation:
    runs: dict[str, Path]   # run name on the site -> VO run folder, absolute
    thumbs_every: int       # every n-th frame of the sequence goes into the atlas
    thumbs_size: tuple[int, int]  # width, height of one thumbnail, px
    thumbs_cols: int


@dataclass(frozen=True)
class Change:
    run: Path               # change run with light normalization, absolute
    run_nonorm: Path        # the same configuration without it, absolute
    config: Path            # change_run.yaml of the run, absolute
    fp_labels: Path         # manual classes of false events, absolute
    examples: Path          # crops the report shows, absolute
    pairs: tuple[str, ...]  # pairs the page shows
    display_width: int      # px of the pictures on the page


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
    engineering: Engineering
    hero: Hero
    detector: Detector
    navigation: Navigation
    change: Change
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

    c, r, eng, h, det, nav, chg = (d['clip'], d['recipe'], d['engineering'], d['hero'], d['detector'],
                                   d['navigation'], d['change'])
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
        facts=tuple(Fact(name=name, file=course / f['file'], match=f.get('match'), list=f.get('list', 'rows'),
                         field=f['field'])
                    for name, f in d['facts'].items()),
        engineering=Engineering(
            engines=tuple(Engine(id=g['id'], bench=course / g['bench'], results=course / g['results'], row=g['row'])
                          for g in eng['engines']),
            scenarios=course / eng['scenarios'],
            stability=course / eng['stability'],
        ),
        hero=Hero(run=h['run'], crf=h['crf'], colors={int(k): v for k, v in h['colors'].items()}),
        detector=Detector(
            onnx_export=course / det['onnx_export'], deploy=course / det['deploy'],
            browser_limits=dict(det['browser_limits']),
            reference_frames=tuple(det['reference_frames']), fixture_min_score=det['fixture_min_score'],
            degradations=course / det['degradations'], curves=course / det['curves'],
            fixtures=(base / det['fixtures']).resolve(),
        ),
        navigation=Navigation(runs={k: course / v for k, v in nav['runs'].items()}, thumbs_every=nav['thumbs']['every'],
                              thumbs_size=tuple(nav['thumbs']['size']), thumbs_cols=nav['thumbs']['cols']),
        change=Change(run=course / chg['run'], run_nonorm=course / chg['run_nonorm'], config=course / chg['config'],
                      fp_labels=course / chg['fp_labels'], examples=course / chg['examples'],
                      pairs=tuple(chg['pairs']), display_width=chg['display_width']),
        recipe=Recipe(out=base / r['out'], train_args=course / r['train_args'],
                      onnx_export=course / r['onnx_export'], train_paths=dict(r['train_paths'])),
    )
