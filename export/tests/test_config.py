from pathlib import Path

import pytest

from site_export.config import load_config


def make_tree(root: Path) -> None:
    (root / 'cv_course' / 'runs').mkdir(parents=True)
    (root / 'cv_course' / 'src' / 'uav_monitor').mkdir(parents=True)
    (root / 'project' / 'site').mkdir(parents=True)
    (root / 'project' / 'site' / 'astro.config.mjs').write_text('', encoding='utf-8')
    (root / 'project' / 'export').mkdir()


def write_config(path: Path, course: str) -> None:
    path.write_text(f"""course: {course}
site: ../site
contract: configs/cv_contract.yaml
eval_classes: configs/eval_classes.json
clip: {{id: '137', size: [960, 540], crf: 25, gop: 10, poster_frame: 0}}
console:
  - {{id: freeze, run: runs/l12_freeze, results: runs/l12_scenarios/results.json, row: freeze}}
facts:
  frozen_detected: {{file: runs/l12_scenarios/results.json, match: {{row: freeze, check: frozen}}, field: ms}}
engineering:
  engines:
    - {{id: tensorrt_t4, bench: runs/l11_bench_trt, results: runs/l11_quality_t4/results.json, row: TRT}}
  scenarios: runs/l12_scenarios/results.json
  stability: runs/l12_stability/stability.json
  finetune: [runs_hw3/b0_640.json, runs_hw3/ft1_640.json]
  resolution: [runs_hw2/baseline_640.json, runs_hw2/imgsz_1280.json]
hero: {{run: nominal, crf: 30, colors: {{0: '#ff77b0'}}}}
detector:
  onnx_export: runs/l11_export/export.json
  deploy: configs/deploy.yaml
  browser_limits: {{wasm: onnx_fp32, webgpu: tensorrt_fp16}}
  reference_frames: [30, 70]
  fixture_min_score: 0.05
  degradations: configs/degradations.yaml
  curves: runs_hw4/degradations/curves.json
  fixtures: ../site/src/lib/detector/fixtures
navigation:
  runs: {{base: runs/l09_vo_base}}
  thumbs: {{every: 8, size: [160, 120], cols: 10}}
change:
  run: runs/chg_r4
  run_nonorm: runs/chg_nonorm_r4
  config: configs/change_run.yaml
  fp_labels: configs/fp_labels.yaml
  examples: images/change
  pairs: [c185]
  display_width: 1344
recipe:
  out: recipe
  train_args: runs_hw3/ft1_train/args.yaml
  onnx_export: runs/l11_export/export.json
  train_paths: {{data: configs/visdrone_coco_classes.yaml}}
""", encoding='utf-8')


def test_paths_resolve_against_config_file(tmp_path, monkeypatch):
    make_tree(tmp_path)
    config = tmp_path / 'project' / 'export' / 'config.yaml'
    write_config(config, '../../cv_course')
    # the working directory must not matter
    monkeypatch.chdir(tmp_path)

    cfg = load_config(Path('project/export/config.yaml'))

    assert cfg.course == (tmp_path / 'cv_course').resolve()
    assert cfg.data_dir == (tmp_path / 'project' / 'site' / 'public' / 'data').resolve()
    assert cfg.console[0].run == cfg.course / 'runs' / 'l12_freeze'
    assert cfg.recipe.out == (tmp_path / 'project' / 'export' / 'recipe').resolve()
    assert cfg.facts[0].list == 'rows'
    assert cfg.hero.colors == {0: '#ff77b0'}


def test_wrong_course_path_fails(tmp_path):
    make_tree(tmp_path)
    config = tmp_path / 'project' / 'export' / 'config.yaml'
    write_config(config, '../cv_course')

    with pytest.raises(FileNotFoundError, match='not a cv_course checkout'):
        load_config(config)
