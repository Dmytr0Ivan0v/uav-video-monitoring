import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';
import { compare } from './compare';
import { decode } from './decode';
import { gaussianKernel, lowLight } from './degrade';
import { letterbox, letterboxParams } from './preprocess';
import type { Box } from './types';

// the fixtures are written by export (export/src/site_export/model.py) with cv2 and numpy
const fixture = <T>(name: string): T =>
  JSON.parse(readFileSync(join(__dirname, 'fixtures', name), 'utf-8')) as T;

interface LetterboxFixture {
  width: number;
  height: number;
  rgb: number[];
  cases: { shape: [number, number]; unpad: [number, number]; top: number; left: number; expected_rgb: number[] }[];
}

interface DecodeFixture {
  output_shape: [number, number, number];
  anchors: number[];
  rows: string;
  frame_hw: [number, number];
  unpad: [number, number];
  top: number;
  left: number;
  conf: number;
  iou: number;
  max_det: number;
  classes: number[];
  expected: Box[];
}

describe('letterbox against cv2', () => {
  const f = fixture<LetterboxFixture>('letterbox.json');
  const picture = { data: Uint8Array.from(f.rgb), width: f.width, height: f.height };

  it.each(f.cases)('places and resizes as Ultralytics and cv2.resize do, $shape', (c) => {
    const { rgb, lb } = letterbox(picture, c.shape);
    expect(lb.unpad).toEqual(c.unpad);
    expect([lb.top, lb.left]).toEqual([c.top, c.left]);
    expect(Array.from(rgb)).toEqual(c.expected_rgb);
  });

  it('rounds half to even like Python', () => {
    expect(letterboxParams(4, 5, [2, 4]).unpad).toEqual([2, 2]);
  });
});

describe('decode and NMS against numpy on a clip frame', () => {
  const f = fixture<DecodeFixture>('decode.json');
  const [, channels, anchors] = f.output_shape;
  // anchors left out of the fixture score below half of conf: zeros change nothing
  const output = new Float32Array(channels * anchors);
  const rows = new Float32Array(Uint8Array.from(Buffer.from(f.rows, 'base64')).buffer);
  f.anchors.forEach((a, k) => {
    for (let c = 0; c < channels; c++) output[c * anchors + a] = rows[k * channels + c]!;
  });
  const lb = { shape: [384, 640] as [number, number], unpad: f.unpad, top: f.top, left: f.left };
  const boxes = decode(output, anchors, lb, f.frame_hw, {
    conf: f.conf,
    iou: f.iou,
    maxDet: f.max_det,
    classes: f.classes,
  });

  it('keeps the same boxes in the same order', () => {
    expect(boxes.map((b) => b[0])).toEqual(f.expected.map((b) => b[0]));
  });

  it('matches coordinates and scores to the rounding of the fixture', () => {
    boxes.forEach((b, i) => {
      const e = f.expected[i]!;
      expect(Math.abs(b[1] - e[1])).toBeLessThanOrEqual(0.0005);
      for (let k = 2; k < 6; k++) expect(Math.abs(b[k]! - e[k]!)).toBeLessThanOrEqual(0.005);
    });
  });

  it('passes the browser check against itself', () => {
    const c = compare(f.expected, boxes, { iouMin: 0.9, maxScoreDiff: 0.02, nearThreshold: 0.15 });
    expect(c.pass).toBe(true);
    expect(c.pairs).toBe(f.expected.length);
  });
});

describe('degradations against OpenCV and numpy', () => {
  const f = fixture<{ kernels: Record<string, number[]>; pixels: number[]; low_light: Record<string, number[]> }>(
    'degrade.json',
  );

  it('builds the blur kernel cv2.GaussianBlur uses', () => {
    for (const [sigma, expected] of Object.entries(f.kernels)) {
      const k = gaussianKernel(Number(sigma));
      expect(k.length, `sigma ${sigma}`).toBe(expected.length);
      k.forEach((v, i) => expect(Math.abs(v - expected[i]!)).toBeLessThan(0.000001));
    }
  });

  it('darkens exactly as np.rint(img * float32(k))', () => {
    // one pixel per value: R, G, B the same, alpha 255
    const data = new Uint8ClampedArray(f.pixels.flatMap((v) => [v, v, v, 255]));
    for (const [k, expected] of Object.entries(f.low_light)) {
      const out = lowLight({ data, width: f.pixels.length, height: 1 }, Number(k));
      expect(Array.from(out.data).filter((_, i) => i % 4 === 0), `k ${k}`).toEqual(expected);
    }
  });
});
