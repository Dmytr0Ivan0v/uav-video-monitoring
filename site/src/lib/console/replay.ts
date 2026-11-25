import type { RunDoc, Status, TrackBox } from './types';

// One output of the pipeline on the timeline: a processed frame or an expected frame that never arrived.
export interface Step {
  frame: number;
  status: Status;
  ms: number[] | null;      // per stage of RunDoc.stages; null for a dropped frame
  tracks: TrackBox[];
  cameraFrozen: boolean;    // the picture repeats an earlier frame, whatever the system reports
  // running totals up to and including this step
  events: number;
  dropped: number;
  frozen: number;
  falseOk: number;          // ok boxes reported from a frozen picture
  newTracks: number;
  endedTracks: number;      // tracks last seen on the previous step
}

export interface TrackPath {
  id: number;
  cls: number;
  points: { frame: number; x: number; y: number }[];  // box centres, source pixels
  scoreSum: number;
}

export interface Replay {
  run: RunDoc;
  steps: Step[];
  tracks: Map<number, TrackPath>;
}

export function cameraFrozenAt(run: RunDoc, frame: number): boolean {
  const f = run.scenario.freeze;
  return f != null && frame > f.start_frame && frame < f.end_frame;
}

export function buildReplay(run: RunDoc): Replay {
  const raw = [
    ...run.frames.map((f) => ({ frame: f.frame, status: f.status as Status, ms: f.ms, tracks: f.tracks })),
    ...run.dropped.map((d) => ({ frame: d.frame, status: 'frame_dropped' as Status, ms: null, tracks: [] })),
  ].sort((a, b) => a.frame - b.frame);

  const tracks = new Map<number, TrackPath>();
  for (const r of raw) {
    for (const [id, cls, score, x1, y1, x2, y2] of r.tracks) {
      let t = tracks.get(id);
      if (!t) {
        t = { id, cls, points: [], scoreSum: 0 };
        tracks.set(id, t);
      }
      t.points.push({ frame: r.frame, x: (x1 + x2) / 2, y: (y1 + y2) / 2 });
      t.scoreSum += score;
    }
  }
  const firstAt = new Map<number, number>();
  const lastAt = new Map<number, number>();
  for (const t of tracks.values()) {
    const a = t.points[0]!.frame;
    const z = t.points[t.points.length - 1]!.frame;
    firstAt.set(a, (firstAt.get(a) ?? 0) + 1);
    lastAt.set(z, (lastAt.get(z) ?? 0) + 1);
  }

  let events = 0, dropped = 0, frozen = 0, falseOk = 0;
  const steps: Step[] = raw.map((r, i) => {
    const cameraFrozen = cameraFrozenAt(run, r.frame);
    // a frame_dropped or frozen step is one event without a box
    events += r.status === 'ok' ? r.tracks.length : 1;
    if (r.status === 'frame_dropped') dropped += 1;
    if (r.status === 'frozen') frozen += 1;
    if (r.status === 'ok' && cameraFrozen) falseOk += r.tracks.length;
    const prev = raw[i - 1];
    return {
      ...r,
      cameraFrozen,
      events,
      dropped,
      frozen,
      falseOk,
      newTracks: firstAt.get(r.frame) ?? 0,
      endedTracks: prev ? (lastAt.get(prev.frame) ?? 0) : 0,
    };
  });
  return { run, steps, tracks };
}

// index of the last step at or before the frame; -1 before the first output
export function stepIndexAt(steps: Step[], frame: number): number {
  let lo = 0, hi = steps.length - 1, found = -1;
  while (lo <= hi) {
    const mid = (lo + hi) >> 1;
    if (steps[mid]!.frame <= frame) {
      found = mid;
      lo = mid + 1;
    } else {
      hi = mid - 1;
    }
  }
  return found;
}
