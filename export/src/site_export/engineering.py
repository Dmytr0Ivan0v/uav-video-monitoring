"""Engineering section: bench runs, scenario results, stability run, eval by object size -> engineering document."""

from pathlib import Path

from site_export.config import Engine, Engineering
from site_export.runs import check_rows, read_json

BENCH_KEYS = ('inference_p50_ms', 'inference_p95_ms', 'step_p95_ms', 'throughput_fps', 'peak_rss_mb')
QUALITY_CHECKS = ('idf1', 'recall', 'p95_ms')
WINDOW_KEYS = ('window', 'frames_timed', 'p50_ms', 'p95_ms', 'rss_mb', 'events_in_memory', 'idf1', 'recall')
SIZES = ('small', 'medium', 'large', 'all')


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


def eval_run(path: Path) -> dict:
    d = read_json(path)
    by_size = d['metrics']['by_size']
    return {
        'name': d['config']['name'],
        'imgsz': d['config']['imgsz'],
        'by_size': {s: {'objects': by_size[s]['objects'], 'map50_95': by_size[s]['mAP50-95']} for s in SIZES},
        'recall': d['metrics']['recall'],
        'time_mean_ms': d['performance']['time_mean_ms'],
    }


# two eval runs compared on one split: the object counts of every size must agree
def size_pair(paths: tuple[Path, Path], course: Path) -> dict:
    runs = [eval_run(p) for p in paths]
    counts = [{s: r['by_size'][s]['objects'] for s in SIZES} for r in runs]
    if counts[0] != counts[1]:
        raise ValueError(f'{paths[0]} and {paths[1]}: different splits, objects {counts[0]} vs {counts[1]}')
    return {'sources': [p.relative_to(course).as_posix() for p in paths], 'runs': runs}


def engineering(cfg: Engineering, course: Path) -> tuple[dict, list[Path]]:
    protocol = read_json(cfg.engines[0].bench / 'bench.json')['protocol']
    doc = {
        'protocol': {k: protocol[k] for k in ('batch', 'warmup', 'iters', 'series')},
        'engines': [engine(e, course) for e in cfg.engines],
        'scenarios': {'source': cfg.scenarios.relative_to(course).as_posix(), 'rows': scenario_rows(cfg.scenarios)},
        'stability': {'source': cfg.stability.relative_to(course).as_posix(), **stability(cfg.stability)},
        'sizes': {'finetune': size_pair(cfg.finetune, course), 'resolution': size_pair(cfg.resolution, course)},
    }
    sources = [p for e in cfg.engines for p in (e.bench / 'bench.json', e.results)]
    return doc, sources + [cfg.scenarios, cfg.stability, *cfg.finetune, *cfg.resolution]
