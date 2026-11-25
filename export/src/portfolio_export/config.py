"""Export configuration: config.yaml -> Config."""

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class Config:
    course: Path        # cv_course checkout, absolute
    site: Path          # Astro project root, absolute

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
    cfg = Config(
        course=(base / d['course']).resolve(),
        site=(base / d['site']).resolve(),
    )
    # runs/ and the package are what every later step reads; a wrong path should fail here
    for need in (cfg.course / 'runs', cfg.course / 'src' / 'uav_monitor'):
        if not need.is_dir():
            raise FileNotFoundError(f'course: {cfg.course} is not a cv_course checkout, missing {need}')
    if not (cfg.site / 'astro.config.mjs').is_file():
        raise FileNotFoundError(f'site: {cfg.site} has no astro.config.mjs')
    return cfg
