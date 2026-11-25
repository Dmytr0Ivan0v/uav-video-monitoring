// public/data/change.json, written by export/src/portfolio_export/change.py

export type PairKind = 'motion' | 'motion_camera' | 'static' | 'light';

export interface ChangeDoc {
  run: string;
  tau: number; // working threshold of the run
  taus: number[]; // thresholds of the curve; mask(taus[k]) = level > k
  mask: { open_kernel: number; thr_area: number };
  proxy: { changed_iou: number; static_iou: number; recall_cover: number };
  align: { orb_features: number; ransac_px: number; min_inliers: number };
  pr_curve: {
    tau: number;
    precision: number;
    recall: number;
    f1: number;
    n_pairs: number;
    n_found: number;
    n_changed: number;
    false_comp_per_pair: number;
  }[];
  pairs: { pair_id: string; kind: PairKind; n_inliers: number; residual_before: number; residual_after: number }[];
  light: { pair: string; false_events: number; false_events_no_normalization: number }[];
  shown: {
    id: string;
    kind: PairKind;
    t0: number;
    t1: number | null;
    inliers: number;
    size: [number, number]; // full frame, px; the mask levels are at this size
    image_t0: string; // earlier frame warped onto the later one, display size
    image_t1: string;
    levels: string;
  }[];
  metrics: Record<string, { tau: number; n_changed: number; n_found: number; mask_px: number; n_false_comp: number }[]>;
  fp_review: { run: string; counts: Record<string, number> };
  examples: { pair: string; kind: 'changed' | 'false' | 'missed'; image: string; label: string | null }[];
}
