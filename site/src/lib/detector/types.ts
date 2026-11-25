// public/data/detector.json, written by export/src/portfolio_export/model.py

// model class id, score, x1, y1, x2, y2 in image pixels
export type Box = [number, number, number, number, number, number];

export type Backend = 'webgpu' | 'wasm';

export type DegradationType = 'blur' | 'noise' | 'low_light' | 'jpeg';

export interface DetectorDoc {
  model: {
    path: string;
    bytes: number;
    sha256: string;
    weights_sha256: string;
    input: [number, number, number, number];
    output: [number, number, number];
    opset: number;
  };
  inference: { conf: number; iou: number; max_det: number; classes: number[] };
  browser_tolerance: { iou_min: number; near_threshold: number; max_score_diff: Record<Backend, number> };
  references: { frame: number; image: string; boxes: Box[] }[];
  degradations: {
    seed: number;
    types: Record<DegradationType, { param: string; levels: (number | null)[] }>;
  };
  curves: {
    type: DegradationType;
    level: number;
    value: number | null;
    'mAP50-95': number;
    'small_mAP50-95': number;
    precision: number;
    recall: number;
    delta_rel_pct: number;
  }[];
}

// an RGBA picture as canvas ImageData holds it
export interface Picture {
  data: Uint8ClampedArray | Uint8Array;
  width: number;
  height: number;
}
