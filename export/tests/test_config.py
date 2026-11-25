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
    path.write_text(f"""course: {course}
site: ../site
contract: configs/cv_contract.yaml
eval_classes: configs/eval_classes.json
clip: {{id: '137', size: [960, 540], crf: 25, gop: 10, poster_frame: 0}}
console:
  - {{id: freeze, run: runs/l12_freeze, results: runs/l12_scenarios/results.json, row: freeze}}
facts:
  frozen_detected: {{results: runs/l12_scenarios/results.json, row: freeze, check: frozen, field: ms}}
recipe:
  out: recipe
  train_args: runs_hw3/ft1_train/args.yaml
  onnx_export: runs/l11_export/export.json
  train_paths: {{data: configs/visdrone_coco_classes.yaml}}
""", encoding='utf-8')


def test_paths_resolve_against_config_file(tmp_path, monkeypatch):
    make_tree(tmp_path)
    config = tmp_path / 'portfolio' / 'export' / 'config.yaml'
    write_config(config, '../../cv_course')
    # the working directory must not matter
    monkeypatch.chdir(tmp_path)

    cfg = load_config(Path('portfolio/export/config.yaml'))

    assert cfg.course == (tmp_path / 'cv_course').resolve()
    assert cfg.data_dir == (tmp_path / 'portfolio' / 'site' / 'public' / 'data').resolve()
    assert cfg.console[0].run == cfg.course / 'runs' / 'l12_freeze'
    assert cfg.recipe.out == (tmp_path / 'portfolio' / 'export' / 'recipe').resolve()


def test_wrong_course_path_fails(tmp_path):
    make_tree(tmp_path)
    config = tmp_path / 'portfolio' / 'export' / 'config.yaml'
    write_config(config, '../cv_course')

    with pytest.raises(FileNotFoundError, match='not a cv_course checkout'):
        load_config(config)
