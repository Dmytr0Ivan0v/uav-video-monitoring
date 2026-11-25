"""Run folders of cv_course: frames.csv, events.jsonl, manifest.json, run_config.yaml -> records."""

import csv
import json
from dataclasses import dataclass
from pathlib import Path

import yaml

STAGES = ('decode', 'preprocess', 'inference', 'postprocess', 'track_other', 'total')
RUN_FILES = ('frames.csv', 'events.jsonl', 'summary.json', 'manifest.json', 'run_config.yaml')


@dataclass
class Frame:
    frame: int                  # source frame, 0-based; dropped frames are not in frames.csv
    status: str                 # ok | frozen
    ms: tuple[float, ...]       # time per STAGES, ms
    n_tracks: int
    frame_diff: float | None    # mean gray diff to the previous processed frame, 0-255


def read_json(path: Path):
    with path.open(encoding='utf-8') as f:
        return json.load(f)


def read_yaml(path: Path):
    with path.open(encoding='utf-8') as f:
        return yaml.safe_load(f)


def read_frames(run: Path) -> list[Frame]:
    frames = []
    with (run / 'frames.csv').open(encoding='utf-8', newline='') as f:
        for row in csv.DictReader(f):
            diff = row.get('frame_diff')
            frames.append(Frame(
                frame=int(row['frame_idx']),
                # runs before contract v3 have no frozen check: every processed frame went out as ok
                status=row.get('status', 'ok'),
                ms=tuple(round(float(row[f'{s}_ms']), 3) for s in STAGES),
                n_tracks=int(row['n_tracks']),
                frame_diff=round(float(diff), 3) if diff else None,
            ))
    return frames


def read_events(run: Path) -> list[dict]:
    with (run / 'events.jsonl').open(encoding='utf-8') as f:
        return [json.loads(line) for line in f if line.strip()]


def check_rows(results: Path, row: str) -> list[dict]:
    rows = [{k: v for k, v in r.items() if k != 'row'}
            for r in read_json(results)['rows'] if r['row'] == row]
    if not rows:
        raise ValueError(f'{results}: no rows named {row!r}')
    return rows
