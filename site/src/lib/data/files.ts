import { readFileSync } from 'node:fs';
import { join } from 'node:path';

// Build time only: Vite does not import from public/, so pages read the exported JSON from disk.
export function readPublicJson<T>(path: string): T {
  return JSON.parse(readFileSync(join(process.cwd(), 'public', path), 'utf-8')) as T;
}
