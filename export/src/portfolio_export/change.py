"""Change detection runs of cv_course: frame pairs -> aligned pictures, mask levels per threshold, PR curve."""

import csv
import shutil
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from portfolio_export.config import Change
from portfolio_export.outputs import write_json
from portfolio_export.runs import read_yaml


@dataclass(frozen=True)
class Align:
    orb_features: int
    top_matches: int
    ransac_px: float
    min_inliers: int
    normalize_light: bool


def load_gray(path: Path) -> np.ndarray:
    img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise FileNotFoundError(f'cannot read {path}')
    return img


def synth_light(img: np.ndarray, alpha: float, beta: float, noise_sigma: float, rng: np.random.Generator) -> np.ndarray:
    # as uav_monitor.change.synth_light: t1 of a synthetic pair is t0 under other light
    out = img.astype(np.float32) * alpha + beta
    if noise_sigma > 0:
        out += rng.normal(0.0, noise_sigma, img.shape).astype(np.float32)
    return np.clip(np.rint(out), 0, 255).astype(np.uint8)


def align(g0: np.ndarray, g1: np.ndarray, a: Align) -> tuple[np.ndarray, np.ndarray, int]:
    # as uav_monitor.change.align: ORB, cross-checked matches, RANSAC homography, t0 warped onto t1
    orb = cv2.ORB.create(a.orb_features)
    k0, d0 = orb.detectAndCompute(g0, None)
    k1, d1 = orb.detectAndCompute(g1, None)
    matches = sorted(cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True).match(d0, d1), key=lambda m: m.distance)
    matches = matches[:a.top_matches]
    src = np.float32([k0[m.queryIdx].pt for m in matches])
    dst = np.float32([k1[m.trainIdx].pt for m in matches])
    h, inliers = cv2.findHomography(src, dst, cv2.RANSAC, a.ransac_px)
    n = int(inliers.sum())
    if n < a.min_inliers:
        raise ValueError(f'{n} inliers, the course run defers pairs below {a.min_inliers}')
    size = (g1.shape[1], g1.shape[0])
    warped = cv2.warpPerspective(g0, h, size)
    valid = cv2.warpPerspective(np.full_like(g0, 255), h, size) > 0
    return warped, valid, n


def normalize_light(src: np.ndarray, ref: np.ndarray, valid: np.ndarray) -> np.ndarray:
    # as uav_monitor.change.normalize_light: mean and std of t0 matched to t1 inside the valid zone
    s = src[valid].astype(np.float32)
    r = ref[valid].astype(np.float32)
    out = (src.astype(np.float32) - s.mean()) / (s.std() + 0.000001) * r.std() + r.mean()
    out[~valid] = 0
    return np.clip(np.rint(out), 0, 255).astype(np.uint8)


def mask_at(diff: np.ndarray, tau: int, kernel: np.ndarray) -> np.ndarray:
    # as uav_monitor.change.diff_mask: D >= tau, then an opening
    _, mask = cv2.threshold(diff, tau - 1, 255, cv2.THRESH_BINARY)
    return cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)


def mask_levels(diff: np.ndarray, taus: list[int], open_kernel: int) -> np.ndarray:
    # an opening keeps inclusion, so the masks of growing tau are nested: one byte per pixel holds them all,
    # the number of thresholds at which the pixel is in the mask; mask(taus[k]) = levels > k
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (open_kernel, open_kernel))
    levels = np.zeros(diff.shape, np.uint8)
    previous = None
    for tau in sorted(taus):
        m = mask_at(diff, tau, kernel) > 0
        if previous is not None and (m & ~previous).any():
            raise ValueError(f'mask at tau {tau} is not inside the mask of the lower tau')
        levels += m
        previous = m
    return levels


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f))


def num(v: str):
    try:
        return int(v)
    except ValueError:
        return float(v) if v not in ('', 'None') else None


def export_change(c: Change, course: Path, data_dir: Path, media_dir: Path) -> list[tuple[Path, list[Path]]]:
    cfg = read_yaml(c.config)
    seq = cfg['sequence']
    frames = course / cfg['dataset_root'] / seq['frames']
    a = cfg['align']
    al = Align(a['orb_features'], a['top_matches'], a['ransac_px'], a['min_inliers'], a['normalize_light'])
    taus = cfg['metrics']['taus']
    tau = cfg['mask']['tau']
    specs = {p['id']: p for p in cfg['pairs']} | {p['id']: p for p in cfg['synthetic']['pairs']}
    public = data_dir.parent
    outputs, shown = [], []

    for pid in c.pairs:
        p = specs[pid]
        t0 = p.get('t0', p.get('base'))
        g0 = load_gray(frames / seq['frame_pattern'].format(t0))
        sources = [frames / seq['frame_pattern'].format(t0), c.config]
        if 'alpha' in p:
            rng = np.random.default_rng([cfg['synthetic']['seed'], t0])
            g1 = synth_light(g0, p['alpha'], p['beta'], cfg['synthetic']['noise_sigma'], rng)
        else:
            g1 = load_gray(frames / seq['frame_pattern'].format(p['t1']))
            sources.append(frames / seq['frame_pattern'].format(p['t1']))
        warped, valid, inliers = align(g0, g1, al)
        g0a = normalize_light(warped, g1, valid) if al.normalize_light else warped
        diff = cv2.absdiff(g1, g0a)
        diff[~valid] = 0
        levels = mask_levels(diff, taus, cfg['mask']['open_kernel'])

        # the mask of the working tau must be the one of the course run
        course_mask = cv2.imread(str(c.run / 'pairs' / pid / 'mask.png'), cv2.IMREAD_GRAYSCALE)
        ours = levels > taus.index(tau)
        if course_mask is not None and not np.array_equal(ours, course_mask > 0):
            share = float((ours != (course_mask > 0)).mean())
            raise ValueError(f'{pid}: mask at tau {tau} differs from the course run in {share:.6f} of pixels')

        out_dir = media_dir / 'visdrone' / 'change'
        out_dir.mkdir(parents=True, exist_ok=True)
        h = round(g1.shape[0] * c.display_width / g1.shape[1])
        names = {}
        for key, img in (('t0', g0a), ('t1', g1)):
            path = out_dir / f'{pid}_{key}.jpg'
            cv2.imwrite(str(path), cv2.resize(img, (c.display_width, h), interpolation=cv2.INTER_AREA),
                        [cv2.IMWRITE_JPEG_QUALITY, 82])
            names[f'image_{key}'] = path.relative_to(public).as_posix()
            outputs.append((path, sources))
        # full size: the mask is the same pixels as in the course run, the browser only scales the drawing
        path = out_dir / f'{pid}_levels.png'
        cv2.imwrite(str(path), levels, [cv2.IMWRITE_PNG_COMPRESSION, 9])
        names['levels'] = path.relative_to(public).as_posix()
        outputs.append((path, sources))
        shown.append({'id': pid, 'kind': p['kind'], 't0': t0, 't1': p.get('t1'), 'inliers': inliers,
                      'size': [g1.shape[1], g1.shape[0]], **names})

    pairs = {r['pair_id']: {k: num(v) if k not in ('pair_id', 'kind', 'status', 'images') else v
                            for k, v in r.items() if k != 'images'}
             for r in read_csv(c.run / 'pairs.csv')}
    nonorm = {r['pair_id']: num(r['n_ev_false']) for r in read_csv(c.run_nonorm / 'pairs.csv')}
    metrics = {}
    for r in read_csv(c.run / 'metrics.csv'):
        if r['pair_id'] in c.pairs:
            metrics.setdefault(r['pair_id'], []).append({k: num(v) for k, v in r.items() if k not in ('pair_id', 'kind')})
    review = read_yaml(c.fp_labels)
    labels = review['labels']
    counts: dict[str, int] = {}
    for per_pair in labels.values():
        for cls in per_pair.values():
            counts[cls] = counts.get(cls, 0) + 1

    examples = []
    for f in sorted(c.examples.glob('*.png')):
        pid, kind, idx = f.stem.split('_')
        dst = media_dir / 'visdrone' / 'change' / 'examples' / f.name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(f, dst)
        outputs.append((dst, [f]))
        examples.append({'pair': pid, 'kind': kind, 'image': dst.relative_to(public).as_posix(),
                         'label': labels.get(pid, {}).get(int(idx)) if kind == 'false' else None})

    doc = {
        'run': c.run.relative_to(course).as_posix(),
        'tau': tau,
        'taus': taus,
        'mask': {k: cfg['mask'][k] for k in ('open_kernel', 'thr_area')},
        'proxy': {k: cfg['metrics'][k] for k in ('changed_iou', 'static_iou', 'recall_cover')},
        'align': {'orb_features': al.orb_features, 'ransac_px': al.ransac_px, 'min_inliers': al.min_inliers},
        'pr_curve': [{k: num(v) for k, v in r.items()} for r in read_csv(c.run / 'pr_curve.csv')],
        'pairs': list(pairs.values()),
        # false events with and without light normalization: the synthetic light pairs and c205 with auto exposure
        'light': [{'pair': k, 'false_events': pairs[k]['n_ev_false'], 'false_events_no_normalization': nonorm[k]}
                  for k in pairs if pairs[k]['kind'] == 'light' or k == 'c205'],
        'shown': shown,
        'metrics': metrics,
        'fp_review': {'run': review['run'], 'counts': counts},
        'examples': examples,
    }
    out = data_dir / 'change.json'
    write_json(out, doc, compact=False)
    outputs.append((out, [c.config, c.fp_labels] + [c.run / f for f in ('pr_curve.csv', 'pairs.csv', 'metrics.csv')]
                    + [c.run_nonorm / 'pairs.csv']))
    return outputs
