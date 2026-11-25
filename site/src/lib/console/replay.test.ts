import { describe, expect, it } from 'vitest';
import { readPublicJson } from '../data/files';
import { buildReplay, stepIndexAt } from './replay';
import type { RunDoc } from './types';

const run = (id: string) => readPublicJson<RunDoc>(`data/console/${id}.json`);
const check = (doc: RunDoc, name: string) => doc.checks.find((c) => c.check === name)!.ms;

// the counters the console shows at the end of the clip must equal the scenario table
describe('replay of exported runs', () => {
  it('counts ok boxes on the frozen picture when the check is off', () => {
    const doc = run('freeze_nocheck');
    const last = buildReplay(doc).steps.at(-1)!;
    expect(last.falseOk).toBe(check(doc, 'ok_in_freeze'));
    expect(last.frozen).toBe(0);
  });

  it('reports frozen instead of boxes when the check is on', () => {
    const doc = run('freeze');
    const last = buildReplay(doc).steps.at(-1)!;
    expect(last.frozen).toBe(check(doc, 'frozen'));
    expect(last.falseOk).toBe(0);
  });

  it('places every dropped frame on the timeline', () => {
    const doc = run('drop_every');
    const { steps } = buildReplay(doc);
    expect(steps.at(-1)!.dropped).toBe(check(doc, 'frame_dropped'));
    const frames = steps.map((s) => s.frame);
    expect(frames).toEqual([...frames].sort((a, b) => a - b));
  });

  it('finds the step shown at any frame', () => {
    const { steps } = buildReplay(run('nominal'));
    expect(stepIndexAt(steps, -1)).toBe(-1);
    expect(steps[stepIndexAt(steps, 5)]!.frame).toBe(4);
    expect(steps[stepIndexAt(steps, 232)]!.frame).toBe(232);
  });
});
