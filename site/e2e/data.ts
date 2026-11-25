import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import type { APIRequestContext } from '@playwright/test';

// the exported data the pages draw: the tests expect the same numbers on screen
export function publicJson<T>(path: string): T {
  return JSON.parse(readFileSync(join(process.cwd(), 'public', path), 'utf-8')) as T;
}

export function fact(name: string): number {
  return publicJson<Record<string, { value: number }>>('data/facts.json')[name]!.value;
}

// VisDrone media are built locally and are not in git; tests that need the pixels say so and skip
export async function hasMedia(request: APIRequestContext, path: string): Promise<boolean> {
  return (await request.head(path)).ok();
}

export const PAGES = [
  '/',
  '/uk/',
  '/lab/navigation/',
  '/uk/lab/navigation/',
  '/lab/detector/',
  '/uk/lab/detector/',
  '/lab/change/',
  '/uk/lab/change/',
];
