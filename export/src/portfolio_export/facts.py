"""Headline facts: fields of check rows in results.json -> facts document."""

from pathlib import Path

from portfolio_export.config import Fact
from portfolio_export.runs import check_rows


def fact_value(f: Fact):
    rows = [r for r in check_rows(f.results, f.row) if r['check'] == f.check]
    if len(rows) != 1:
        raise ValueError(f'fact {f.name}: {len(rows)} rows {f.row}/{f.check} in {f.results}')
    value = rows[0]
    for key in f.field.split('.'):
        value = value[key]
    return value


def facts(items: tuple[Fact, ...], course: Path) -> dict:
    return {f.name: {'value': fact_value(f), 'source': f.results.relative_to(course).as_posix(),
                     'row': f.row, 'check': f.check, 'field': f.field}
            for f in items}
