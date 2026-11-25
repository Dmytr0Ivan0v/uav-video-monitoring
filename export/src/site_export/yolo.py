"""YOLO detection steps as Ultralytics 8.4 runs them: BGR frame -> input tensor -> boxes in frame pixels.

The browser detector repeats these steps; this module is the reference it is checked against.
"""

from dataclasses import dataclass

import cv2
import numpy as np

PAD_VALUE = 114
MAX_WH = 7680       # class offset for batched NMS, as in Ultralytics


@dataclass
class Letterbox:
    shape: tuple[int, int]      # model input height, width
    unpad: tuple[int, int]      # resized frame width, height inside the input
    top: int
    left: int


@dataclass
class Detections:
    xyxy: np.ndarray            # (n, 4) float32, frame pixels
    score: np.ndarray           # (n,) float32
    cls: np.ndarray             # (n,) int, model class id


def letterbox_params(frame_hw: tuple[int, int], shape: tuple[int, int]) -> Letterbox:
    h, w = frame_hw
    r = min(shape[0] / h, shape[1] / w)
    # Python round is half to even; the browser repeats it
    unpad = round(w * r), round(h * r)
    dw, dh = (shape[1] - unpad[0]) / 2, (shape[0] - unpad[1]) / 2
    return Letterbox(shape=shape, unpad=unpad, top=round(dh - 0.1), left=round(dw - 0.1))


def letterbox(frame: np.ndarray, shape: tuple[int, int]) -> tuple[np.ndarray, Letterbox]:
    lb = letterbox_params(frame.shape[:2], shape)
    img = frame if frame.shape[1::-1] == lb.unpad else cv2.resize(frame, lb.unpad, interpolation=cv2.INTER_LINEAR)
    bottom = shape[0] - lb.unpad[1] - lb.top
    right = shape[1] - lb.unpad[0] - lb.left
    img = cv2.copyMakeBorder(img, lb.top, bottom, lb.left, right, cv2.BORDER_CONSTANT, value=(PAD_VALUE,) * 3)
    return img, lb


def to_tensor(img_bgr: np.ndarray) -> np.ndarray:
    return np.ascontiguousarray(img_bgr[..., ::-1].transpose(2, 0, 1)[None], dtype=np.float32) / 255


def iou_one(box: np.ndarray, boxes: np.ndarray) -> np.ndarray:
    x1 = np.maximum(box[0], boxes[:, 0])
    y1 = np.maximum(box[1], boxes[:, 1])
    x2 = np.minimum(box[2], boxes[:, 2])
    y2 = np.minimum(box[3], boxes[:, 3])
    inter = np.clip(x2 - x1, 0, None) * np.clip(y2 - y1, 0, None)
    area = (box[2] - box[0]) * (box[3] - box[1])
    areas = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])
    return inter / (area + areas - inter)


def nms(boxes: np.ndarray, scores: np.ndarray, iou: float) -> list[int]:
    # greedy, highest score first; a box goes when its IoU with a kept one is strictly above the threshold
    order = np.argsort(-scores, kind='stable')
    keep = []
    while order.size:
        i = order[0]
        keep.append(int(i))
        order = order[1:][iou_one(boxes[i], boxes[order[1:]]) <= iou]
    return keep


def decode(raw: np.ndarray, lb: Letterbox, frame_hw: tuple[int, int], conf: float, iou: float,
           classes: list[int], max_det: int) -> Detections:
    pred = raw[0].T                                 # (anchors, 4 + classes)
    scores_all = pred[:, 4:]
    # candidates by the best of all classes, then the class filter, as Ultralytics does
    best = scores_all.argmax(1)
    score = scores_all[np.arange(len(pred)), best]
    keep = (score > conf) & np.isin(best, classes)
    xywh, score, best = pred[keep, :4], score[keep], best[keep]
    xyxy = np.concatenate([xywh[:, :2] - xywh[:, 2:] / 2, xywh[:, :2] + xywh[:, 2:] / 2], axis=1)
    idx = nms(xyxy + best[:, None] * MAX_WH, score, iou)[:max_det]
    xyxy, score, best = xyxy[idx], score[idx], best[idx]

    h, w = frame_hw
    gain_x, gain_y = lb.unpad[0] / w, lb.unpad[1] / h
    xyxy = (xyxy - [lb.left, lb.top, lb.left, lb.top]) / [gain_x, gain_y, gain_x, gain_y]
    xyxy = np.clip(xyxy, 0, [w, h, w, h]).astype(np.float32)
    return Detections(xyxy=xyxy, score=score.astype(np.float32), cls=best)
