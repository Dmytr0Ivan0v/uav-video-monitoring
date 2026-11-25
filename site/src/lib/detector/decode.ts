// Model output -> boxes in picture pixels, step for step as export/src/site_export/yolo.py (Ultralytics 8.4).
import type { Letterbox } from './preprocess';
import type { Box } from './types';

const MAX_WH = 7680; // class offset for batched NMS

export interface DecodeParams {
  conf: number;
  iou: number;
  maxDet: number;
  classes: number[];
}

const f32 = Math.fround;

// IoU in float32, as numpy computes it on float32 boxes
function iou(a: Float32Array, i: number, j: number): number {
  const x1 = Math.max(a[i * 4]!, a[j * 4]!);
  const y1 = Math.max(a[i * 4 + 1]!, a[j * 4 + 1]!);
  const x2 = Math.min(a[i * 4 + 2]!, a[j * 4 + 2]!);
  const y2 = Math.min(a[i * 4 + 3]!, a[j * 4 + 3]!);
  const inter = f32(Math.max(f32(x2 - x1), 0) * Math.max(f32(y2 - y1), 0));
  const areaI = f32(f32(a[i * 4 + 2]! - a[i * 4]!) * f32(a[i * 4 + 3]! - a[i * 4 + 1]!));
  const areaJ = f32(f32(a[j * 4 + 2]! - a[j * 4]!) * f32(a[j * 4 + 3]! - a[j * 4 + 1]!));
  return f32(inter / f32(f32(areaI + areaJ) - inter));
}

// greedy, highest score first; a box goes when its IoU with a kept one is strictly above the threshold
export function nms(boxes: Float32Array, scores: Float32Array, threshold: number): number[] {
  const order = Array.from(scores.keys()).sort((a, b) => scores[b]! - scores[a]!);
  const removed = new Uint8Array(scores.length);
  const keep: number[] = [];
  for (let p = 0; p < order.length; p++) {
    const i = order[p]!;
    if (removed[i]) continue;
    keep.push(i);
    for (let q = p + 1; q < order.length; q++) {
      const j = order[q]!;
      if (!removed[j] && iou(boxes, i, j) > threshold) removed[j] = 1;
    }
  }
  return keep;
}

// output: model output (1, 4 + classes, anchors) flattened; frame: height, width of the picture
export function decode(
  output: Float32Array,
  anchors: number,
  lb: Letterbox,
  frame: [number, number],
  p: DecodeParams,
): Box[] {
  const nc = output.length / anchors - 4;
  const kept: number[] = [];
  const cls: number[] = [];
  const score: number[] = [];
  for (let a = 0; a < anchors; a++) {
    // candidates by the best of all classes, then the class filter, as Ultralytics does
    let best = 0;
    let s = output[4 * anchors + a]!;
    for (let c = 1; c < nc; c++) {
      const v = output[(4 + c) * anchors + a]!;
      if (v > s) {
        s = v;
        best = c;
      }
    }
    if (s > p.conf && p.classes.includes(best)) {
      kept.push(a);
      cls.push(best);
      score.push(s);
    }
  }

  const n = kept.length;
  const xyxy = new Float32Array(n * 4);
  const shifted = new Float32Array(n * 4);
  for (let k = 0; k < n; k++) {
    const a = kept[k]!;
    const cx = output[a]!;
    const cy = output[anchors + a]!;
    const hw = f32(output[2 * anchors + a]! / 2);
    const hh = f32(output[3 * anchors + a]! / 2);
    xyxy.set([f32(cx - hw), f32(cy - hh), f32(cx + hw), f32(cy + hh)], k * 4);
    for (let i = 0; i < 4; i++) shifted[k * 4 + i] = f32(xyxy[k * 4 + i]! + cls[k]! * MAX_WH);
  }
  const keep = nms(shifted, Float32Array.from(score), p.iou).slice(0, p.maxDet);

  const [h, w] = frame;
  const gx = lb.unpad[0] / w;
  const gy = lb.unpad[1] / h;
  return keep.map((k) => {
    const x1 = Math.min(Math.max((xyxy[k * 4]! - lb.left) / gx, 0), w);
    const y1 = Math.min(Math.max((xyxy[k * 4 + 1]! - lb.top) / gy, 0), h);
    const x2 = Math.min(Math.max((xyxy[k * 4 + 2]! - lb.left) / gx, 0), w);
    const y2 = Math.min(Math.max((xyxy[k * 4 + 3]! - lb.top) / gy, 0), h);
    return [cls[k]!, score[k]!, f32(x1), f32(y1), f32(x2), f32(y2)];
  });
}
