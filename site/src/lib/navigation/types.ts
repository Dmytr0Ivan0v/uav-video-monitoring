// public/data/navigation.json, written by export/src/portfolio_export/vo.py

// t from the first frame s, x y z m, qx qy qz qw, error m, status index, inliers, frame;
// positions and orientation in the motion-capture frame, z up, after one SE3 alignment
export type Pose = [number, number, number, number, number, number, number, number, number, number, number, number];

export interface VoRun {
  run: string;
  degradation: { type: string; length_px: number; angle_deg: number } | null;
  ate_m: { rmse: number; median: number; max: number };
  rpe: { delta: number; unit: 's' | 'm'; pairs: number; trans_rmse_m: number; trans_median_m: number; rot_mean_deg: number }[];
  status_counts: Record<string, number>;
  median_inliers: number;
  statuses: string[];
  poses: Pose[];
  atlas: { image: string; cols: number; size: [number, number]; every: number; count: number };
}

export interface NavigationDoc {
  sequence: string;
  gt_path_length_m: number;
  alignment: string;
  association_max_difference_s: number;
  estimated_poses: number;
  gt: [number, number, number, number][]; // t, x, y, z of the matched ground truth poses, same order as poses
  runs: Record<'base' | 'blur', VoRun>;
}
