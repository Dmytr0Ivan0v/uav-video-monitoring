"""Weights recipe: fine-tune args and ONNX export record of cv_course -> export/recipe/."""

from site_export.config import Recipe
from site_export.outputs import write_json, write_yaml
from site_export.runs import read_json, read_yaml

# what reproduces the model; timings, warnings and the host are left in cv_course
ONNX_KEYS = ('command', 'weights', 'weights_sha256', 'export', 'opset', 'inputs', 'outputs',
             'onnx_sha256', 'onnx_mb', 'versions', 'git')


def train_args(r: Recipe) -> dict:
    args = read_yaml(r.train_args)
    for key, path in r.train_paths.items():
        args[key] = path
    left = [k for k, v in args.items() if isinstance(v, str) and v.startswith('/')]
    if left:
        raise ValueError(f'{r.train_args}: absolute paths left in {left}, add them to recipe.train_paths')
    return args


def onnx_export(r: Recipe) -> dict:
    record = read_json(r.onnx_export)
    return {k: record[k] for k in ONNX_KEYS}


def write_recipe(r: Recipe) -> list[str]:
    write_yaml(r.out / 'train_args.yaml', train_args(r))
    write_json(r.out / 'onnx_export.json', onnx_export(r), compact=False)
    return ['train_args.yaml', 'onnx_export.json']
