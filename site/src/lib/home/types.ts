import type { CheckRow } from '../console/types';

// public/data/facts.json: one field of one course file per name
export type FactsDoc = Record<string, { value: number | string; source: string; field: string }>;

export interface EngineRow {
  id: 'pytorch_cpu' | 'onnx_cpu' | 'pytorch_t4' | 'tensorrt_t4';
  engine: string;
  precision: string;
  cpu: string;
  gpu: string | null;
  bench: {
    inference_p50_ms: number;
    inference_p95_ms: number;
    step_p95_ms: number;
    throughput_fps: number;
    peak_rss_mb: number;
  };
  quality: { idf1: CheckRow; recall: CheckRow; p95_ms: CheckRow };
  sources: string[];
}

export interface StabilityCheck {
  check: string;
  reference: number | [number, number];
  value: number;
  threshold: number | string;
  result: 'pass' | 'fail';
  per_window_mb?: number;
  windows_per_span?: number;
  hours?: number;
}

// public/data/engineering.json
export interface EngineeringDoc {
  protocol: { batch: number; warmup: number; iters: number; series: number };
  engines: EngineRow[];
  scenarios: { source: string; rows: Record<string, CheckRow[]> };
  stability: {
    source: string;
    window_video_s: number;
    rss_start_mb: number;
    windows: {
      window: number;
      frames_timed: number;
      p50_ms: number;
      p95_ms: number;
      rss_mb: number;
      events_in_memory: number;
      idf1: number;
      recall: number;
    }[];
    checks: StabilityCheck[];
  };
}
