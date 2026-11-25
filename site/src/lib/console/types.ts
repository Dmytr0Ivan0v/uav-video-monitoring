// Shapes of the files export writes to public/data/console and public/data/visdrone.

export type Status = 'ok' | 'frame_dropped' | 'frozen';

// track_id, model class id, score, x1, y1, x2, y2 in source pixels
export type TrackBox = [number, number, number, number, number, number, number];

// target id, model class id, x1, y1, x2, y2 in source pixels
export type GtBox = [number, number, number, number, number, number];

export interface ClipDoc {
  id: string;
  name: string;
  fps: number;
  frames: number;
  source_size: [number, number];
  video_size: [number, number];
  vid_stride: number;
  contract: {
    version: number;
    statuses: Status[];
    frame_budget_ms: number;
    latency_p95_ms: number;
  };
  classes: Record<string, string>;
  media: {
    video: string;
    poster: string;
    stills: Record<string, string>;
  };
}

export interface FrameDoc {
  frame: number;
  t: number;
  status: 'ok' | 'frozen';
  ms: number[];
  n_tracks: number;
  frame_diff: number | null;
  tracks: TrackBox[];
}

export interface CheckRow {
  check: string;
  frames: 'all' | 'common' | null;
  m0: number | [number, number] | null;
  ms: number;
  delta_rel: number | null;
  threshold: number | string | null;
  result: 'pass' | 'fail' | null;
  detail?: Record<string, unknown>;
  excluded_mot_frames?: [number, number];
  excluded_count?: number;
}

export interface RunDoc {
  id: string;
  run: string;
  engine: {
    weights: string;
    device: string;
    cpu: string;
    gpu: string | null;
  };
  scenario: {
    id: string;
    kind: string;
    freeze?: { start_frame: number; end_frame: number } | null;
    drop_every?: { every: number } | null;
  };
  stages: string[];
  frames: FrameDoc[];
  dropped: { frame: number; t: number }[];
  summary: Record<string, unknown>;
  checks: CheckRow[];
}

export interface GtDoc {
  clip: string;
  frames: { frame: number; boxes: GtBox[] }[];
}
