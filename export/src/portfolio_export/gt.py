"""VisDrone MOT annotations -> ground truth boxes per frame in model class ids."""

import csv
from pathlib import Path

from portfolio_export.runs import read_json


def class_map(eval_classes: Path) -> tuple[dict[int, int], dict[int, str]]:
    to_model, names = {}, {}
    for name, c in read_json(eval_classes).items():
        names[c['coco_id']] = name
        for v in c['visdrone_ids']:
            to_model[v] = c['coco_id']
    return to_model, names


def read_gt(path: Path, to_model: dict[int, int]) -> list[dict]:
    frames: dict[int, list[list[int]]] = {}
    with path.open(encoding='utf-8', newline='') as f:
        # frame, target, x, y, w, h, score, category, truncation, occlusion; frame is 1-based
        for row in csv.reader(f):
            frame, target, x, y, w, h, score, category = map(int, row[:8])
            # score 0 marks boxes the evaluation ignores; categories 0 and 11 have no model class
            if score == 0 or category not in to_model:
                continue
            frames.setdefault(frame - 1, []).append([target, to_model[category], x, y, x + w, y + h])
    return [{'frame': k, 'boxes': sorted(v)} for k, v in sorted(frames.items())]
