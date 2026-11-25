import pytest

from portfolio_export.config import Recipe
from portfolio_export.recipe import train_args

ARGS = """model: yolo11s.pt
data: /home/user/notebooks/configs/visdrone_coco_classes.yaml
project: /home/user/notebooks/runs_hw3
epochs: 10
"""


def recipe(tmp_path, train_paths):
    path = tmp_path / 'args.yaml'
    path.write_text(ARGS, encoding='utf-8')
    return Recipe(out=tmp_path / 'recipe', train_args=path, onnx_export=tmp_path / 'export.json',
                  train_paths=train_paths)


def test_training_machine_paths_become_course_paths(tmp_path):
    args = train_args(recipe(tmp_path, {'data': 'configs/visdrone_coco_classes.yaml', 'project': 'runs_hw3'}))

    assert args == {'model': 'yolo11s.pt', 'data': 'configs/visdrone_coco_classes.yaml',
                    'project': 'runs_hw3', 'epochs': 10}


def test_absolute_path_left_in_args_fails(tmp_path):
    with pytest.raises(ValueError, match=r"absolute paths left in \['project'\]"):
        train_args(recipe(tmp_path, {'data': 'configs/visdrone_coco_classes.yaml'}))
