from pathlib import Path

import pytest

from portfolio_export.config import load_config


def make_tree(root: Path) -> None:
    (root / 'cv_course' / 'runs').mkdir(parents=True)
    (root / 'cv_course' / 'src' / 'uav_monitor').mkdir(parents=True)
    (root / 'portfolio' / 'site').mkdir(parents=True)
    (root / 'portfolio' / 'site' / 'astro.config.mjs').write_text('', encoding='utf-8')
    (root / 'portfolio' / 'export').mkdir()


def write_config(path: Path, course: str) -> None:
    path.write_text(f'course: {course}\nsite: ../site\n', encoding='utf-8')


def test_paths_resolve_against_config_file(tmp_path, monkeypatch):
    make_tree(tmp_path)
    config = tmp_path / 'portfolio' / 'export' / 'config.yaml'
    write_config(config, '../../cv_course')
    # the working directory must not matter
    monkeypatch.chdir(tmp_path)

    cfg = load_config(Path('portfolio/export/config.yaml'))

    assert cfg.course == (tmp_path / 'cv_course').resolve()
    assert cfg.data_dir == (tmp_path / 'portfolio' / 'site' / 'public' / 'data').resolve()


def test_wrong_course_path_fails(tmp_path):
    make_tree(tmp_path)
    config = tmp_path / 'portfolio' / 'export' / 'config.yaml'
    write_config(config, '../cv_course')

    with pytest.raises(FileNotFoundError, match='not a cv_course checkout'):
        load_config(config)
