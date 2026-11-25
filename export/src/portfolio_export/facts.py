"""Facts for the site texts: fields of course result files (JSON, YAML, CSV) -> facts document."""

import csv
from pathlib import Path

from portfolio_export.config import Fact
from portfolio_export.runs import read_json, read_yaml


def number(text: str) -> int | float | str:
    for cast in (int, float):
        try:
            return cast(text)
        except ValueError:
            pass
    return text


def load(path: Path):
    if path.suffix == '.json':
        return read_json(path)
    if path.suffix in ('.yaml', '.yml'):
        return read_yaml(path)
    if path.suffix == '.csv':
        with path.open(encoding='utf-8', newline='') as f:
            return [{k: number(v) for k, v in row.items()} for row in csv.DictReader(f)]
    raise ValueError(f'{path}: no reader for {path.suffix}')


def fact_value(f: Fact):
    doc = load(f.file)
    if f.match:
        items = doc if isinstance(doc, list) else doc[f.list]
        hits = [r for r in items if all(r.get(k) == v for k, v in f.match.items())]
        if len(hits) != 1:
            raise ValueError(f'fact {f.name}: {len(hits)} rows match {f.match} in {f.file}')
        doc = hits[0]
    for key in f.field.split('.'):
        doc = doc[key]
    return doc


def facts(items: tuple[Fact, ...], course: Path) -> dict:
    out = {}
    for f in items:
        entry = {'value': fact_value(f), 'source': f.file.relative_to(course).as_posix()}
        if f.match:
            entry['match'] = f.match
        entry['field'] = f.field
        out[f.name] = entry
    return out
