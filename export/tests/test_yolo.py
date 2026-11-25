import numpy as np

from site_export.yolo import decode, letterbox_params

CLASSES = [0, 2]


def raw_output(rows: list[tuple]) -> np.ndarray:
    # made-up model output: (1, 4 + 3 classes, anchors), rows are cx, cy, w, h, then class scores
    return np.array(rows, dtype=np.float32).T[None]


def test_letterbox_of_a_clip_frame():
    lb = letterbox_params((1512, 2688), (384, 640))

    assert lb.unpad == (640, 360)
    assert (lb.top, lb.left) == (12, 0)


def test_letterbox_rounds_half_to_even_as_python():
    # 4 x 5 into 2 x 4: r = 0.5, the width 2.5 rounds to 2, where Math.round would give 3
    lb = letterbox_params((4, 5), (2, 4))

    assert lb.unpad == (2, 2)
    assert lb.left == 1


def test_decode_keeps_the_best_box_per_class_and_maps_to_the_frame():
    lb = letterbox_params((20, 40), (20, 40))     # same size: no scale, no padding
    raw = raw_output([
        (10, 10, 4, 4, 0.9, 0.0, 0.0),            # class 0
        (10.5, 10, 4, 4, 0.8, 0.0, 0.0),          # class 0, overlaps the first: suppressed
        (10, 10, 4, 4, 0.0, 0.0, 0.7),            # class 2 at the same place: kept
        (30, 10, 4, 4, 0.05, 0.6, 0.0),           # best class 1 is not kept, though class 0 is in the list
        (30, 10, 4, 4, 0.09, 0.0, 0.0),           # below conf
    ])

    d = decode(raw, lb, (20, 40), conf=0.1, iou=0.7, classes=CLASSES, max_det=10)

    assert d.cls.tolist() == [0, 2]
    assert np.allclose(d.score, [0.9, 0.7])
    assert np.allclose(d.xyxy[0], [8, 8, 12, 12])
