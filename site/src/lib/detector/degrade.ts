// Picture degradations of the robustness homework (configs/degradations.yaml), applied before the letterbox.
// low light is the same formula as numpy; blur uses the OpenCV kernel in floating point (OpenCV rounds in fixed point);
// noise and JPEG are approximations: another random generator, the browser JPEG encoder.
import { roundHalfEven } from './preprocess';
import type { DegradationType, Picture } from './types';

function clamp8(v: number): number {
  return v < 0 ? 0 : v > 255 ? 255 : v;
}

function copy(p: Picture): Picture {
  return { data: new Uint8ClampedArray(p.data), width: p.width, height: p.height };
}

// img * float32(k), np.rint, clip
export function lowLight(p: Picture, k: number): Picture {
  const out = copy(p);
  const kf = Math.fround(k);
  for (let i = 0; i < out.data.length; i++) {
    if (i % 4 !== 3) out.data[i] = clamp8(roundHalfEven(Math.fround(p.data[i]! * kf)));
  }
  return out;
}

// cv2.getGaussianKernel for the size cv2.GaussianBlur picks on 8-bit pictures: round(6 sigma + 1), odd
export function gaussianKernel(sigma: number): Float64Array {
  const size = roundHalfEven(sigma * 6 + 1) | 1;
  const k = new Float64Array(size);
  let sum = 0;
  for (let i = 0; i < size; i++) {
    const x = i - (size - 1) / 2;
    k[i] = Math.exp(-(x * x) / (2 * sigma * sigma));
    sum += k[i]!;
  }
  return k.map((v) => v / sum);
}

// OpenCV BORDER_REFLECT_101: ...2 1 | 0 1 2 ... n-1 | n-2 ...
function reflect101(i: number, n: number): number {
  if (n === 1) return 0;
  while (i < 0 || i >= n) i = i < 0 ? -i : 2 * n - 2 - i;
  return i;
}

export function blur(p: Picture, sigma: number): Picture {
  const k = gaussianKernel(sigma);
  const r = (k.length - 1) / 2;
  const { width: w, height: h } = p;
  const tmp = new Float32Array(w * h * 3);
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      for (let c = 0; c < 3; c++) {
        let s = 0;
        for (let t = -r; t <= r; t++) s += k[t + r]! * p.data[(y * w + reflect101(x + t, w)) * 4 + c]!;
        tmp[(y * w + x) * 3 + c] = s;
      }
    }
  }
  const out = copy(p);
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      for (let c = 0; c < 3; c++) {
        let s = 0;
        for (let t = -r; t <= r; t++) s += k[t + r]! * tmp[(reflect101(y + t, h) * w + x) * 3 + c]!;
        out.data[(y * w + x) * 4 + c] = clamp8(roundHalfEven(s));
      }
    }
  }
  return out;
}

// a small seeded generator; numpy's PCG64 field cannot be repeated here, so the noise is the same kind, not the same
function mulberry32(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export function noise(p: Picture, sigma: number, seed: number): Picture {
  const rand = mulberry32(seed);
  const out = copy(p);
  for (let i = 0; i < out.data.length; i += 4) {
    for (let c = 0; c < 3; c++) {
      // Box-Muller: one standard normal value per pixel and channel
      const n = Math.sqrt(-2 * Math.log(1 - rand())) * Math.cos(2 * Math.PI * rand());
      out.data[i + c] = clamp8(roundHalfEven(p.data[i + c]! + sigma * n));
    }
  }
  return out;
}

// browser JPEG encoder at the same quality number; the encoder is not libjpeg as OpenCV builds it
export async function jpeg(p: Picture, quality: number): Promise<Picture> {
  const canvas = new OffscreenCanvas(p.width, p.height);
  canvas.getContext('2d')!.putImageData(new ImageData(new Uint8ClampedArray(p.data), p.width, p.height), 0, 0);
  const blob = await canvas.convertToBlob({ type: 'image/jpeg', quality: quality / 100 });
  const bitmap = await createImageBitmap(blob);
  const back = new OffscreenCanvas(p.width, p.height);
  const ctx = back.getContext('2d')!;
  ctx.drawImage(bitmap, 0, 0);
  return ctx.getImageData(0, 0, p.width, p.height);
}

export async function degrade(
  p: Picture,
  type: DegradationType | null,
  value: number | null,
  seed: number,
): Promise<Picture> {
  if (type == null || value == null) return p;
  if (type === 'blur') return value > 0 ? blur(p, value) : p;
  if (type === 'noise') return value > 0 ? noise(p, value, seed) : p;
  if (type === 'low_light') return value !== 1 ? lowLight(p, value) : p;
  return jpeg(p, value);
}
