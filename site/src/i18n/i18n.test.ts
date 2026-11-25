import { describe, expect, it } from 'vitest';
import { storyVars } from '../lib/console/checks';
import { ENGINES, STREAMS } from '../lib/console/runs';
import type { RunDoc } from '../lib/console/types';
import { readPublicJson } from '../lib/data/files';
import { fill } from '../lib/format';
import { factVars } from '../lib/home/facts';
import type { FactsDoc } from '../lib/home/types';
import { DICTS } from './index';

const facts = factVars(readPublicJson<FactsDoc>('data/facts.json'));
const runs = [...STREAMS, ...ENGINES].map((id) => [id, readPublicJson<RunDoc>(`data/console/${id}.json`)] as const);

describe.each(Object.values(DICTS))('$lang dictionary', (t) => {
  it('names every check and threshold the exported runs contain', () => {
    for (const [, run] of runs) {
      for (const row of run.checks) {
        expect(t.console.checks, row.check).toHaveProperty(row.check);
        if (typeof row.threshold === 'string') expect(Object.keys(t.console.thresholds)).toContain(row.threshold);
      }
    }
  });

  it('fills every story from the numbers of its run', () => {
    for (const [id, run] of runs) {
      for (const p of t.console.stories[id]) expect(() => fill(p, storyVars(run))).not.toThrow();
    }
  });

  it('fills every fact of the main page from facts.json', () => {
    const h = t.home;
    const templates = [
      ...h.facts.flatMap((f) => [f.value, f.text]),
      ...h.decisions.items.flatMap((d) => [d.problem, d.decision, d.result, d.cost]),
      h.engineering.engines.text,
    ];
    for (const p of templates) expect(() => fill(p, facts), p).not.toThrow();
  });
});
