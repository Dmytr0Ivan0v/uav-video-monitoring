"""Visual odometry runs of cv_course: TUM trajectory + ground truth -> aligned poses, errors, frame atlas."""

import csv
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from portfolio_export.runs import read_json, read_yaml

STATUSES = ['INIT', 'OK', 'DEGRADED', 'LOST']


@dataclass
class Trajectory:
    stamps: np.ndarray      # (n,), s
    t: np.ndarray           # (n, 3), m
    q: np.ndarray           # (n, 4), x y z w


def read_tum(path: Path) -> Trajectory:
    with path.open(encoding='utf-8') as f:
        rows = np.array([[float(v) for v in line.split()[:8]] for line in f if line.strip() and not line.startswith('#')])
    return Trajectory(stamps=rows[:, 0], t=rows[:, 1:4], q=rows[:, 4:8])


def associate(t_a: np.ndarray, t_b: np.ndarray, max_difference: float) -> list[tuple[int, int]]:
    # as uav_monitor.vo.associate: the closest pairs first, each stamp once; t_b sorted
    candidates = []
    for i, t in enumerate(t_a):
        j0 = int(np.searchsorted(t_b, t))
        for j in (j0 - 1, j0):
            if 0 <= j < len(t_b) and abs(t - t_b[j]) < max_difference:
                candidates.append((abs(t - t_b[j]), i, j))
    used_a, used_b, pairs = set(), set(), []
    for _, i, j in sorted(candidates):
        if i not in used_a and j not in used_b:
            used_a.add(i)
            used_b.add(j)
            pairs.append((i, j))
    return sorted(pairs)


def umeyama_se3(src: np.ndarray, dst: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    # R, t minimising sum ||dst - (R src + t)||^2, as uav_monitor.vo_metrics.umeyama without scale
    mu_s, mu_d = src.mean(0), dst.mean(0)
    u, _, vt = np.linalg.svd((dst - mu_d).T @ (src - mu_s) / len(src))
    s = np.diag([1.0, 1.0, np.sign(np.linalg.det(u @ vt))])
    r = u @ s @ vt
    return r, mu_d - r @ mu_s


def rot_from_quat(q: np.ndarray) -> np.ndarray:
    x, y, z, w = q / np.linalg.norm(q)
    return np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
    ])


def quat_from_rot(r: np.ndarray) -> np.ndarray:
    # as uav_monitor.vo.quat_from_rot: x y z w with w >= 0
    trace = np.trace(r)
    if trace > 0:
        s = 2.0 * np.sqrt(trace + 1.0)
        q = [(r[2, 1] - r[1, 2]) / s, (r[0, 2] - r[2, 0]) / s, (r[1, 0] - r[0, 1]) / s, 0.25 * s]
    else:
        i = int(np.argmax(np.diag(r)))
        j, k = (i + 1) % 3, (i + 2) % 3
        s = 2.0 * np.sqrt(1.0 + r[i, i] - r[j, j] - r[k, k])
        q = [0.0, 0.0, 0.0, (r[k, j] - r[j, k]) / s]
        q[i], q[j], q[k] = 0.25 * s, (r[j, i] + r[i, j]) / s, (r[k, i] + r[i, k]) / s
    q = np.array(q)
    return q if q[3] >= 0 else -q


def motion_blur(gray: np.ndarray, length_px: int, angle_deg: float) -> np.ndarray:
    # as uav_monitor.vo.motion_blur: the degradation the blur run fed to VO
    kernel = np.zeros((length_px, length_px), np.float32)
    kernel[length_px // 2, :] = 1.0
    rot = cv2.getRotationMatrix2D((length_px / 2 - 0.5, length_px / 2 - 0.5), angle_deg, 1.0)
    kernel = cv2.warpAffine(kernel, rot, (length_px, length_px))
    return cv2.filter2D(gray, -1, kernel / kernel.sum())


def read_log(run: Path) -> list[dict]:
    with (run / 'vo_log.csv').open(encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f))


def atlas(images: list[np.ndarray], cols: int) -> np.ndarray:
    h, w = images[0].shape[:2]
    rows = -(-len(images) // cols)
    sheet = np.zeros((rows * h, cols * w), np.uint8)
    for k, img in enumerate(images):
        r, c = divmod(k, cols)
        sheet[r * h:(r + 1) * h, c * w:(c + 1) * w] = img
    return sheet


@dataclass(frozen=True)
class Thumbs:
    every: int                  # every n-th frame of the sequence goes into the atlas
    size: tuple[int, int]       # width, height of one thumbnail, px
    cols: int


def run_doc(run: Path, course: Path, out_atlas: Path, public: Path, thumbs: Thumbs) -> tuple[dict, dict]:
    info = read_yaml(run / 'run_config.yaml')
    cfg = info['config']
    evaluation = read_json(run / 'eval.json')
    seq_dir = course / info['sequence_dir']
    calib = read_yaml(run / 'calibration.yaml')

    est = read_tum(run / 'trajectory.tum')
    gt = read_tum(seq_dir / cfg['sequence']['gt'])
    pairs = associate(est.stamps, gt.stamps + calib['time_offset_s'], cfg['association_max_difference_s'])
    ie, ig = (np.array(v) for v in zip(*pairs))
    r, t = umeyama_se3(est.t[ie], gt.t[ig])
    aligned = est.t[ie] @ r.T + t
    err = np.linalg.norm(gt.t[ig] - aligned, axis=1)

    # the alignment of the course run, recomputed: the page shows the poses it measured
    ate = {'rmse': round(float(np.sqrt((err ** 2).mean())), 4), 'median': round(float(np.median(err)), 4),
           'max': round(float(err.max()), 4)}
    if ate != evaluation['ate_m'] or len(pairs) != evaluation['comparison']['associated_poses']:
        raise ValueError(f'{run}: ATE {ate} on {len(pairs)} poses, eval.json has {evaluation["ate_m"]} '
                         f'on {evaluation["comparison"]["associated_poses"]}')

    log = {round(float(row['timestamp']), 6): row for row in read_log(run)}
    t0 = float(next(iter(log)))
    poses = []
    for k, (i, j) in enumerate(pairs):
        row = log[round(float(est.stamps[i]), 6)]
        q = quat_from_rot(r @ rot_from_quat(est.q[i]))
        poses.append([round(float(est.stamps[i]) - t0, 3), *np.round(aligned[k], 4).tolist(), *np.round(q, 4).tolist(),
                      round(float(err[k]), 4), STATUSES.index(row['status']), int(row['inliers']), int(row['frame'])])

    # thumbnails of what VO saw: the gray frame, degraded as in the run
    with (seq_dir / 'rgb.txt').open(encoding='utf-8') as f:
        rgb = [line.split()[1] for line in f if line.strip() and not line.startswith('#')]
    deg = cfg.get('degradation') or {}
    frames = list(range(0, len(rgb), thumbs.every))
    images = []
    for n in frames:
        gray = cv2.imread(str(seq_dir / rgb[n]), cv2.IMREAD_GRAYSCALE)
        if deg.get('type') == 'motion_blur':
            gray = motion_blur(gray, deg['motion_blur']['length_px'], deg['motion_blur']['angle_deg'])
        images.append(cv2.resize(gray, thumbs.size, interpolation=cv2.INTER_AREA))
    out_atlas.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_atlas), atlas(images, thumbs.cols), [cv2.IMWRITE_JPEG_QUALITY, 80])

    doc = {
        'run': run.relative_to(course).as_posix(),
        'degradation': ({'type': deg['type'], **deg['motion_blur']} if deg.get('type') == 'motion_blur' else None),
        'ate_m': ate,
        'rpe': evaluation['rpe'],
        'status_counts': evaluation['status_counts'],
        'median_inliers': evaluation['median_inliers'],
        'statuses': STATUSES,
        # t from the first frame s, x y z m, qx qy qz qw, error m, status index, inliers, frame
        'poses': poses,
        'atlas': {'image': out_atlas.relative_to(public).as_posix(), 'cols': thumbs.cols, 'size': list(thumbs.size),
                  'every': thumbs.every, 'count': len(frames)},
    }
    shared = {
        'sequence': cfg['sequence']['dir'],
        'gt_path_length_m': evaluation['gt_path_length_m'],
        'alignment': evaluation['comparison']['alignment'],
        'association_max_difference_s': evaluation['comparison']['association_max_difference_s'],
        'estimated_poses': evaluation['comparison']['estimated_poses'],
        'gt': [[round(float(gt.stamps[j]) - t0, 3), *np.round(gt.t[j], 4).tolist()] for j in ig],
    }
    return doc, shared
