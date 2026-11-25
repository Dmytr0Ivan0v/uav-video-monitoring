"""Browser model: ONNX of the course -> site model, reference boxes on clip frames, test fixtures."""

import base64
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
import shutil

import onnxruntime as ort

from site_export.config import Config
from site_export.outputs import sha256, write_json
from site_export.runs import read_json, read_yaml
from site_export.yolo import Detections, decode, letterbox, to_tensor


@dataclass(frozen=True)
class Inference:
    shape: tuple[int, int]      # model input height, width
    conf: float
    iou: float
    max_det: int
    classes: list[int]          # model class ids kept after NMS


def session(path: Path) -> ort.InferenceSession:
    return ort.InferenceSession(path, providers=['CPUExecutionProvider'])


def raw_output(sess: ort.InferenceSession, frame: np.ndarray, inf: Inference):
    img, lb = letterbox(frame, inf.shape)
    return sess.run(None, {sess.get_inputs()[0].name: to_tensor(img)})[0], lb


def detect(sess: ort.InferenceSession, frame: np.ndarray, inf: Inference) -> Detections:
    raw, lb = raw_output(sess, frame, inf)
    return decode(raw, lb, frame.shape[:2], inf.conf, inf.iou, inf.classes, inf.max_det)


def read_frames(video: Path, indices: list[int]) -> dict[int, np.ndarray]:
    cap = cv2.VideoCapture(str(video))
    frames, i = {}, 0
    while i <= max(indices):
        ok, frame = cap.read()
        if not ok:
            raise ValueError(f'{video}: ends before frame {max(indices)}')
        if i in indices:
            frames[i] = frame
        i += 1
    cap.release()
    return frames


def boxes_doc(d: Detections) -> list[list]:
    return [[int(c), round(float(s), 3), *(round(float(v), 2) for v in xyxy)]
            for c, s, xyxy in zip(d.cls, d.score, d.xyxy)]


def save_frame(frame: np.ndarray, path: Path, size: tuple[int, int]) -> np.ndarray:
    path.parent.mkdir(parents=True, exist_ok=True)
    # PNG: the browser decodes exactly the pixels Python reads back
    cv2.imwrite(str(path), cv2.resize(frame, size, interpolation=cv2.INTER_AREA), [cv2.IMWRITE_PNG_COMPRESSION, 9])
    return cv2.imread(str(path))


def letterbox_fixture() -> dict:
    # a small made-up gradient: the test needs resize and padding, not VisDrone pixels;
    # 40 px rows go through the vector code only, 43 px rows end with a scalar value
    h, w = 31, 53
    y, x = np.mgrid[0:h, 0:w]
    rgb = np.stack([(x * 255) // (w - 1), (y * 255) // (h - 1), ((x + y) * 7) % 256], -1).astype(np.uint8)
    cases = []
    for shape in ((24, 40), (25, 43)):
        img, lb = letterbox(rgb[..., ::-1], shape)
        cases.append({'shape': list(shape), 'unpad': list(lb.unpad), 'top': lb.top, 'left': lb.left,
                      'expected_rgb': img[..., ::-1].reshape(-1).tolist()})
    return {
        'source': 'export/src/site_export/model.py: letterbox_fixture, cv2 ' + cv2.__version__,
        'width': w, 'height': h, 'rgb': rgb.reshape(-1).tolist(),
        'cases': cases,
    }


def degrade_fixture(types: dict) -> dict:
    # kernels cv2.GaussianBlur builds for 8-bit pictures, and low light on a made-up row of pixels
    pixels = np.arange(0, 256, 5, dtype=np.uint8)
    return {
        'source': 'export/src/site_export/model.py: degrade_fixture, cv2 ' + cv2.__version__,
        'kernels': {str(s): cv2.getGaussianKernel(int(round(s * 6 + 1)) | 1, s).ravel().tolist()
                    for s in types['blur']['levels'] if s},
        'pixels': pixels.tolist(),
        'low_light': {str(k): np.clip(np.rint(pixels * np.float32(k)), 0, 255).astype(np.uint8).tolist()
                      for k in types['low_light']['levels'] if k != 1},
    }


def decode_fixture(sess: ort.InferenceSession, frame: np.ndarray, inf: Inference, frame_no: int,
                   min_score: float) -> dict:
    raw, lb = raw_output(sess, frame, inf)
    d = decode(raw, lb, frame.shape[:2], inf.conf, inf.iou, inf.classes, inf.max_det)
    pred = raw[0]                                   # (4 + classes, anchors)
    # anchors below min_score can never become candidates at conf, so the test fills them with zeros
    keep = np.flatnonzero(pred[4:].max(0) >= min_score)
    return {
        'source': f'model output on reference frame {frame_no} of the clip',
        'output_shape': list(raw.shape),
        'anchors': keep.tolist(),
        'rows': base64.b64encode(np.ascontiguousarray(pred[:, keep].T, dtype='<f4').tobytes()).decode(),
        'frame_hw': list(frame.shape[:2]),
        'unpad': list(lb.unpad), 'top': lb.top, 'left': lb.left,
        'conf': inf.conf, 'iou': inf.iou, 'max_det': inf.max_det, 'classes': inf.classes,
        'expected': boxes_doc(d),
    }


def export_model(cfg: Config, video: Path) -> list[tuple[Path, list[Path]]]:
    det = cfg.detector
    deploy = read_yaml(det.deploy)
    record = read_json(det.onnx_export)
    src = cfg.course / record['onnx']
    if sha256(src) != record['onnx_sha256']:
        raise ValueError(f'{src}: sha256 differs from {det.onnx_export}')
    # conf, iou, max_det of the nominal run the quality check used; classes of the evaluation
    run_cfg_path = cfg.course / deploy['quality']['run_config']
    run = read_yaml(run_cfg_path)['inference']
    classes = sorted(c['coco_id'] for c in read_json(cfg.eval_classes).values())
    inf = Inference(shape=tuple(deploy['export']['imgsz']), conf=run['conf'], iou=run['iou'],
                    max_det=run['max_det'], classes=classes)

    public = cfg.site / 'public'
    model = public / 'models' / src.name
    model.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, model)
    sess = session(model)

    frames = read_frames(video, list(det.reference_frames))
    refs, pngs = [], []
    for k in det.reference_frames:
        png = cfg.media_dir / 'visdrone' / 'detector' / f'frame_{k:03d}.png'
        img = save_frame(frames[k], png, cfg.clip.size)
        refs.append({'frame': k, 'image': png.relative_to(public).as_posix(), 'boxes': boxes_doc(detect(sess, img, inf))})
        pngs.append(png)

    degradations = read_yaml(det.degradations)
    det.fixtures.mkdir(parents=True, exist_ok=True)
    write_json(det.fixtures / 'degrade.json', degrade_fixture(degradations['types']))
    write_json(det.fixtures / 'letterbox.json', letterbox_fixture())
    write_json(det.fixtures / 'decode.json',
               decode_fixture(sess, cv2.imread(str(pngs[0])), inf, det.reference_frames[0], det.fixture_min_score))

    c = deploy['consistency']
    doc = {
        'model': {
            'path': model.relative_to(public).as_posix(),
            'bytes': model.stat().st_size,
            'sha256': record['onnx_sha256'],
            'weights_sha256': record['weights_sha256'],
            'input': list(sess.get_inputs()[0].shape),
            'output': list(sess.get_outputs()[0].shape),
            'opset': record['opset'],
        },
        'inference': {'conf': inf.conf, 'iou': inf.iou, 'max_det': inf.max_det, 'classes': inf.classes},
        'browser_tolerance': {
            'iou_min': c['iou_min'],
            'near_threshold': c['near_threshold'],
            'max_score_diff': {backend: c['max_score_diff'][key] for backend, key in det.browser_limits.items()},
        },
        'references': refs,
        'degradations': {'seed': degradations['seed'],
                         'types': {k: {'param': v['param'], 'levels': v['levels']} for k, v in degradations['types'].items()}},
        'curves': [{k: r[k] for k in ('type', 'level', 'value', 'mAP50-95', 'small_mAP50-95', 'precision', 'recall',
                                      'delta_rel_pct')} for r in read_json(det.curves)['rows']],
    }
    out = cfg.data_dir / 'detector.json'
    write_json(out, doc, compact=False)
    return ([(model, [src]), (out, [det.onnx_export, det.deploy, run_cfg_path, cfg.eval_classes, det.degradations, det.curves])]
            + [(png, [video]) for png in pngs])
