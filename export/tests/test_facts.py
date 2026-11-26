import json

import pytest

from site_export.config import Fact
from site_export.facts import fact_value

# OVERALL and bicycle lines of runs/l10_s4_blur/eval.csv, cut to three columns
EVAL_CSV = """class,idf1,num_switches,recall
bicycle,0.039,12,0.021
OVERALL,0.395,475,0.442
"""
# two S4 rows of runs/l10_scenarios/results.json, cut to four fields
SCENARIOS = {'rows': [
    {'row': 'S4', 'check': 'idf1', 'delta_rel': 0.006, 'threshold': 0.15},
    {'row': 'S4', 'check': 'recall', 'delta_rel': 0.08, 'threshold': 0.15},
]}


def fact(path, match, field):
    return Fact(name='f', file=path, match=match, field=field)


def test_csv_cell_is_a_number(tmp_path):
    path = tmp_path / 'eval.csv'
    path.write_text(EVAL_CSV, encoding='utf-8')

    assert fact_value(fact(path, {'class': 'bicycle'}, 'recall')) == 0.021
    assert fact_value(fact(path, {'class': 'OVERALL'}, 'num_switches')) == 475


def test_json_row_from_rows(tmp_path):
    path = tmp_path / 'results.json'
    path.write_text(json.dumps(SCENARIOS), encoding='utf-8')

    assert fact_value(fact(path, {'row': 'S4', 'check': 'recall'}, 'delta_rel')) == 0.08


def test_match_must_pick_exactly_one_row(tmp_path):
    path = tmp_path / 'results.json'
    path.write_text(json.dumps(SCENARIOS), encoding='utf-8')

    with pytest.raises(ValueError, match='2 rows match'):
        fact_value(fact(path, {'row': 'S4'}, 'delta_rel'))
