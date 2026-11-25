import json

import pytest

from site_export.config import Fact
from site_export.facts import fact_value

# OVERALL and bicycle lines of runs/l10_s4_blur/eval.csv, cut to three columns
EVAL_CSV = """class,idf1,num_switches,recall
bicycle,0.039,12,0.021
OVERALL,0.395,475,0.442
"""
# two rows of runs/l12_stability/stability.json checks
STABILITY = {'checks': [
    {'check': 'p95_growth_rel', 'value': 0.008, 'result': 'pass'},
    {'check': 'rss_growth_extrapolated_mb', 'value': 3307.7, 'result': 'fail'},
]}


def fact(path, match, field, list_key='rows'):
    return Fact(name='f', file=path, match=match, list=list_key, field=field)


def test_csv_cell_is_a_number(tmp_path):
    path = tmp_path / 'eval.csv'
    path.write_text(EVAL_CSV, encoding='utf-8')

    assert fact_value(fact(path, {'class': 'bicycle'}, 'recall')) == 0.021
    assert fact_value(fact(path, {'class': 'OVERALL'}, 'num_switches')) == 475


def test_json_row_from_a_named_list(tmp_path):
    path = tmp_path / 'stability.json'
    path.write_text(json.dumps(STABILITY), encoding='utf-8')

    f = fact(path, {'check': 'rss_growth_extrapolated_mb'}, 'value', list_key='checks')

    assert fact_value(f) == 3307.7


def test_match_must_pick_exactly_one_row(tmp_path):
    path = tmp_path / 'stability.json'
    path.write_text(json.dumps(STABILITY), encoding='utf-8')

    with pytest.raises(ValueError, match='0 rows match'):
        fact_value(fact(path, {'check': 'rss_growth_mb'}, 'value', list_key='checks'))
