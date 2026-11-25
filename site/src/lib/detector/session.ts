// ONNX Runtime Web session: WebGPU when the browser has it, WASM otherwise. Loaded on demand.
// The runtime finds its .wasm next to its own chunk (new URL(..., import.meta.url)), which Vite builds into _astro.
import type { Backend } from './types';

export interface Session {
  backend: Backend;
  run(input: Float32Array, dims: number[]): Promise<Float32Array>;
}

export async function webgpuAvailable(): Promise<boolean> {
  const gpu = (navigator as Navigator & { gpu?: { requestAdapter(): Promise<unknown> } }).gpu;
  if (!gpu) return false;
  try {
    return (await gpu.requestAdapter()) != null;
  } catch {
    return false;
  }
}

// the model is large: read it as a stream to show progress. The total comes from the export, not from
// Content-Length: nginx sends the model gzipped, and the stream counts bytes after decompression
export async function fetchModel(url: string, onProgress: (loaded: number) => void): Promise<Uint8Array> {
  const r = await fetch(url);
  if (!r.ok || !r.body) throw new Error(`${url}: HTTP ${r.status}`);
  const chunks: Uint8Array[] = [];
  let loaded = 0;
  const reader = r.body.getReader();
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    chunks.push(value);
    loaded += value.length;
    onProgress(loaded);
  }
  const out = new Uint8Array(loaded);
  let at = 0;
  for (const c of chunks) {
    out.set(c, at);
    at += c.length;
  }
  return out;
}

export async function createSession(model: Uint8Array, backend: Backend): Promise<Session> {
  const ort = await import('onnxruntime-web/webgpu');
  // threads need SharedArrayBuffer, which the browser gives only to a cross-origin isolated page
  ort.env.wasm.numThreads = globalThis.crossOriginIsolated ? Math.min(4, navigator.hardwareConcurrency || 1) : 1;
  const session = await ort.InferenceSession.create(model, { executionProviders: [backend] });
  const [input] = session.inputNames;
  const [output] = session.outputNames;
  return {
    backend,
    async run(data, dims) {
      const result = await session.run({ [input!]: new ort.Tensor('float32', data, dims) });
      return (await result[output!]!.getData()) as Float32Array;
    },
  };
}
