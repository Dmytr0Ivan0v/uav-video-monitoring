import shutil
from pathlib import Path

import pytest

from site_export.console import scenario

# frames 98-104 of runs/l12_freeze: two ok frames with their first two events, then two frozen frames
FIXTURES = Path(__file__).parent / 'fixtures'
EXCERPT = FIXTURES / 'l12_freeze_excerpt'
DROPPED = '{"frame": null, "t": 0.267, "status": "frame_dropped", "track_id": null, "cls": null, "score": null, "xyxy": null}\n'


def checks(frozen: int) -> list[dict]:
    # rows shaped as in runs/l12_scenarios/results.json, counts of this excerpt
    return [
        {'check': 'frozen', 'ms': frozen, 'detail': {'freeze_frames': [101, 129]}},
        {'check': 'ok_in_freeze', 'ms': 0, 'detail': {'freeze_frames': [101, 129]}},
    ]


def test_excerpt_replays_frozen_frames_without_tracks():
    doc = scenario('freeze', EXCERPT, FIXTURES, checks(frozen=2), fps=30)

    assert [f['frame'] for f in doc['frames']] == [98, 100, 102, 104]
    assert [f['status'] for f in doc['frames']] == ['ok', 'ok', 'frozen', 'frozen']
    assert doc['frames'][1]['tracks'][0] == [3, 2, 0.885, 554.01, 631.47, 752.32, 763.34]
    assert doc['frames'][2]['tracks'] == []
    assert doc['frames'][2]['t'] == 3.4
    assert doc['run'] == 'l12_freeze_excerpt'


def test_count_differing_from_results_fails():
    with pytest.raises(ValueError, match='frozen from events is 2, results.json has 14'):
        scenario('freeze', EXCERPT, FIXTURES, checks(frozen=14), fps=30)


def test_dropped_frame_comes_from_expected_time(tmp_path):
    run = tmp_path / 'run'
    shutil.copytree(EXCERPT, run)
    with (run / 'events.jsonl').open('a', encoding='utf-8') as f:
        f.write(DROPPED)

    doc = scenario('freeze', run, tmp_path, checks(frozen=2), fps=30)

    assert doc['dropped'] == [{'frame': 8, 't': 0.267}]
