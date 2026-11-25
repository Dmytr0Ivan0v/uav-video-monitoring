"""Engineering section: bench runs, scenario results, stability run -> engineering document."""

from pathlib import Path

from portfolio_export.config import Engine, Engineering
from portfolio_export.runs import check_rows, read_json

BENCH_KEYS = ('inference_p50_ms', 'inference_p95_ms', 'step_p95_ms', 'throughput_fps', 'peak_rss_mb')
QUALITY_CHECKS = ('idf1', 'recall', 'p95_ms')
WINDOW_KEYS = ('window', 'frames_timed', 'p50_ms', 'p95_ms', 'rss_mb', 'events_in_memory', 'idf1', 'recall')


def engine(e: Engine, course: Path) -> dict:
    bench = read_json(e.bench / 'bench.json')
    quality = {r['check']: r for r in check_rows(e.results, e.row)}
    return {
        'id': e.id,
        'engine': bench['engine'],
        'precision': bench['precision'],
        'cpu': bench['hardware']['cpu'],
        'gpu': bench['hardware'].get('gpu'),
        'bench': {k: bench['summary'][k] for k in BENCH_KEYS},
        'quality': {k: quality[k] for k in QUALITY_CHECKS},
        'sources': [(e.bench / 'bench.json').relative_to(course).as_posix(), e.results.relative_to(course).as_posix()],
    }


def scenario_rows(results: Path) -> dict[str, list[dict]]:
    rows: dict[str, list[dict]] = {}
    for r in read_json(results)['rows']:
        rows.setdefault(r['row'], []).append({k: v for k, v in r.items() if k != 'row'})
    return rows


def stability(path: Path) -> dict:
    d = read_json(path)
    return {
        'window_video_s': d['window_video_s'],
        'rss_start_mb': d['rss_start_mb'],
        'windows': [{k: w[k] for k in WINDOW_KEYS} for w in d['windows']],
        'checks': d['checks'],
    }


def engineering(cfg: Engineering, course: Path) -> tuple[dict, list[Path]]:
    protocol = read_json(cfg.engines[0].bench / 'bench.json')['protocol']
    doc = {
        'protocol': {k: protocol[k] for k in ('batch', 'warmup', 'iters', 'series')},
        'engines': [engine(e, course) for e in cfg.engines],
        'scenarios': {'source': cfg.scenarios.relative_to(course).as_posix(), 'rows': scenario_rows(cfg.scenarios)},
        'stability': {'source': cfg.stability.relative_to(course).as_posix(), **stability(cfg.stability)},
    }
    sources = [p for e in cfg.engines for p in (e.bench / 'bench.json', e.results)]
    return doc, sources + [cfg.scenarios, cfg.stability]
