// Picture -> model input, as Ultralytics LetterBox does it with cv2.resize(INTER_LINEAR) and padding 114.
import type { Picture } from './types';

export const PAD_VALUE = 114;
const COEF_SCALE = 2048; // OpenCV INTER_RESIZE_COEF_SCALE: 8-bit resize runs in fixed point

export interface Letterbox {
  shape: [number, number]; // model input height, width
  unpad: [number, number]; // resized picture width, height
  top: number;
  left: number;
}

// Python round: half to even
export function roundHalfEven(v: number): number {
  const r = Math.round(v);
  // + 0 turns the -0 of Math.round(-0.1) into 0
  return (Math.abs(v % 1) === 0.5 && r % 2 !== 0 ? r - 1 : r) + 0;
}

export function letterboxParams(height: number, width: number, shape: [number, number]): Letterbox {
  const r = Math.min(shape[0] / height, shape[1] / width);
  const unpad: [number, number] = [roundHalfEven(width * r), roundHalfEven(height * r)];
  const dw = (shape[1] - unpad[0]) / 2;
  const dh = (shape[0] - unpad[1]) / 2;
  return { shape, unpad, top: roundHalfEven(dh - 0.1), left: roundHalfEven(dw - 0.1) };
}

// OpenCV saturate_cast<short>(float): round half to even
function fixed(v: number): number {
  return roundHalfEven(v * COEF_SCALE);
}

interface Taps {
  index: Int32Array; // first source pixel
  a0: Int32Array; // fixed-point weight of it
  a1: Int32Array; // fixed-point weight of the next one
}

// clampEdges: OpenCV zeroes the weight past the edge for columns, rows only clamp the row index
function taps(dst: number, src: number, clampEdges: boolean): Taps {
  const scale = src / dst;
  const index = new Int32Array(dst);
  const a0 = new Int32Array(dst);
  const a1 = new Int32Array(dst);
  for (let d = 0; d < dst; d++) {
    // OpenCV computes the source position in float
    let f = Math.fround((d + 0.5) * scale - 0.5);
    let s = Math.floor(f);
    f = Math.fround(f - s);
    if (clampEdges && s < 0) {
      s = 0;
      f = 0;
    }
    if (clampEdges && s >= src - 1) {
      s = src - 1;
      f = 0;
    }
    index[d] = s;
    a0[d] = fixed(Math.fround(1 - f));
    a1[d] = fixed(f);
  }
  return { index, a0, a1 };
}

// cv2.resize INTER_LINEAR on 8-bit RGB(A): separable, fixed point, with the rounding of OpenCV's 8-bit code
export function resizeRgb(src: Picture, width: number, height: number): Uint8Array {
  const out = new Uint8Array(width * height * 3);
  const tx = taps(width, src.width, true);
  const ty = taps(height, src.height, false);
  const row = (y: number) => Math.min(Math.max(y, 0), src.height - 1);
  const stride = src.data.length / (src.width * src.height); // 3 or 4 channels
  const rowBuf = [new Int32Array(width * 3), new Int32Array(width * 3)];
  const hRow = (y: number, buf: Int32Array) => {
    const base = y * src.width;
    for (let x = 0; x < width; x++) {
      const i0 = (base + tx.index[x]!) * stride;
      const i1 = (base + Math.min(tx.index[x]! + 1, src.width - 1)) * stride;
      for (let c = 0; c < 3; c++) buf[x * 3 + c] = src.data[i0 + c]! * tx.a0[x]! + src.data[i1 + c]! * tx.a1[x]!;
    }
  };
  for (let y = 0; y < height; y++) {
    hRow(row(ty.index[y]!), rowBuf[0]!);
    hRow(row(ty.index[y]! + 1), rowBuf[1]!);
    const b0 = ty.a0[y]!;
    const b1 = ty.a1[y]!;
    const n = width * 3;
    for (let i = 0; i < n; i++) {
      // the 8-bit specialisation of VResizeLinear, vector and scalar code alike, not the generic FixedPtCast
      const v = ((((rowBuf[0]![i]! >> 4) * b0) >> 16) + (((rowBuf[1]![i]! >> 4) * b1) >> 16) + 2) >> 2;
      out[y * n + i] = v < 0 ? 0 : v > 255 ? 255 : v;
    }
  }
  return out;
}

// letterboxed RGB, height x width x 3
export function letterbox(src: Picture, shape: [number, number]): { rgb: Uint8Array; lb: Letterbox } {
  const lb = letterboxParams(src.height, src.width, shape);
  const [w, h] = lb.unpad;
  // at the same size the weights are 2048 and 0, so resizing returns the picture as it is
  const resized = resizeRgb(src, w, h);
  const rgb = new Uint8Array(shape[0] * shape[1] * 3).fill(PAD_VALUE);
  for (let y = 0; y < h; y++) {
    rgb.set(resized.subarray(y * w * 3, (y + 1) * w * 3), ((y + lb.top) * shape[1] + lb.left) * 3);
  }
  return { rgb, lb };
}

// RGB height x width x 3 -> float32 1 x 3 x height x width in 0..1
export function toTensor(rgb: Uint8Array, shape: [number, number]): Float32Array {
  const [h, w] = shape;
  const plane = h * w;
  const out = new Float32Array(3 * plane);
  for (let i = 0; i < plane; i++) {
    out[i] = rgb[i * 3]! / 255;
    out[plane + i] = rgb[i * 3 + 1]! / 255;
    out[2 * plane + i] = rgb[i * 3 + 2]! / 255;
  }
  return out;
}
