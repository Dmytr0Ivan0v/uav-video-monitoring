// Browser boxes against the Python reference, by the consistency protocol of the course (configs/deploy.yaml).
import type { Box } from './types';

export interface Tolerance {
  iouMin: number; // a pair: same class, IoU at least this
  maxScoreDiff: number; // |score difference| of a pair
  nearThreshold: number; // a box without a pair is allowed only below this score
}

export interface Comparison {
  reference: number;
  browser: number;
  pairs: number;
  scoreDiffMax: number;
  scoreDiffP95: number;
  pairIouMin: number;
  pairsOverLimit: number;
  unmatchedNear: number;
  unmatchedFar: number;
  pass: boolean;
}

function boxIou(a: Box, b: Box): number {
  const w = Math.max(0, Math.min(a[4], b[4]) - Math.max(a[2], b[2]));
  const h = Math.max(0, Math.min(a[5], b[5]) - Math.max(a[3], b[3]));
  const inter = w * h;
  return inter / ((a[4] - a[2]) * (a[5] - a[3]) + (b[4] - b[2]) * (b[5] - b[3]) - inter);
}

// the best free pair first: all same-class pairs over iouMin, by IoU from high to low
export function match(ref: Box[], other: Box[], iouMin: number): [number, number, number][] {
  const cand: [number, number, number][] = [];
  ref.forEach((a, i) =>
    other.forEach((b, j) => {
      if (a[0] !== b[0]) return;
      const v = boxIou(a, b);
      if (v >= iouMin) cand.push([i, j, v]);
    }),
  );
  cand.sort((x, y) => y[2] - x[2]);
  const usedRef = new Set<number>();
  const usedOther = new Set<number>();
  const pairs: [number, number, number][] = [];
  for (const [i, j, v] of cand) {
    if (usedRef.has(i) || usedOther.has(j)) continue;
    usedRef.add(i);
    usedOther.add(j);
    pairs.push([i, j, v]);
  }
  return pairs;
}

// numpy percentile with linear interpolation, on sorted values
function percentile(sorted: number[], q: number): number {
  if (!sorted.length) return 0;
  const pos = q * (sorted.length - 1);
  const lo = Math.floor(pos);
  const hi = Math.min(lo + 1, sorted.length - 1);
  return sorted[lo]! + (sorted[hi]! - sorted[lo]!) * (pos - lo);
}

export function compare(ref: Box[], browser: Box[], t: Tolerance): Comparison {
  const pairs = match(ref, browser, t.iouMin);
  const diffs = pairs.map(([i, j]) => Math.abs(ref[i]![1] - browser[j]![1])).sort((a, b) => a - b);
  const inRef = new Set(pairs.map((p) => p[0]));
  const inBrowser = new Set(pairs.map((p) => p[1]));
  const unmatched = [
    ...ref.filter((_, i) => !inRef.has(i)),
    ...browser.filter((_, j) => !inBrowser.has(j)),
  ].map((b) => b[1]);
  const far = unmatched.filter((s) => s >= t.nearThreshold).length;
  const over = diffs.filter((d) => d > t.maxScoreDiff).length;
  return {
    reference: ref.length,
    browser: browser.length,
    pairs: pairs.length,
    scoreDiffMax: diffs.at(-1) ?? 0,
    scoreDiffP95: percentile(diffs, 0.95),
    pairIouMin: pairs.length ? Math.min(...pairs.map((p) => p[2])) : 1,
    pairsOverLimit: over,
    unmatchedNear: unmatched.length - far,
    unmatchedFar: far,
    pass: over === 0 && far === 0,
  };
}
