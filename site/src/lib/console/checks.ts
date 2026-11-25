import type { CheckRow, RunDoc } from './types';

const DIGITS: Record<string, number> = { idf1: 3, recall: 3, precision: 3, p95_ms: 1 };

function num(check: string, v: number): string {
  const d = DIGITS[check];
  return d === undefined ? String(v) : v.toFixed(d);
}

export function valueText(row: CheckRow, which: 'm0' | 'ms'): string {
  const v = row[which];
  if (v == null) return '-';
  if (Array.isArray(v)) {
    const [a, b] = v;
    return a === b ? num(row.check, a) : `${num(row.check, a)}-${num(row.check, b)}`;
  }
  return num(row.check, v);
}

export function deltaText(row: CheckRow): string {
  return row.delta_rel == null ? '-' : row.delta_rel.toFixed(3);
}

// 0.075 -> '7.5%': arithmetic on the exported share, for prose only
export function percent(share: number): string {
  return `${Number((share * 100).toFixed(1))}%`;
}

export function row(run: RunDoc, check: string): CheckRow | undefined {
  return run.checks.find((c) => c.check === check);
}

// only rows with a limit have a result; the rest are shown for context
export function limits(run: RunDoc): { passed: number; total: number } {
  const judged = run.checks.filter((c) => c.result != null);
  return { passed: judged.filter((c) => c.result === 'pass').length, total: judged.length };
}

// numbers the scenario story quotes; every one is a field of the run or of its check rows
export function storyVars(run: RunDoc): Record<string, string> {
  const vars: Record<string, string> = {};
  const idf1 = row(run, 'idf1');
  if (idf1) {
    vars.idf1 = valueText(idf1, 'ms');
    if (idf1.delta_rel != null) vars.idf1Drop = percent(idf1.delta_rel);
    if (typeof idf1.threshold === 'number') vars.idf1Limit = percent(idf1.threshold);
  }
  const frozen = row(run, 'frozen');
  if (frozen) vars.frozen = String(frozen.ms);
  const falseOk = row(run, 'ok_in_freeze');
  if (falseOk) vars.falseOk = String(falseOk.ms);
  const sw = row(run, 'switches_window');
  if (sw) {
    vars.switchesBefore = valueText(sw, 'm0');
    vars.switchesAfter = valueText(sw, 'ms');
  }
  const p95 = row(run, 'p95_ms');
  if (p95) {
    vars.p95Before = valueText(p95, 'm0');
    vars.p95 = valueText(p95, 'ms');
  }
  vars.dropped = String(run.dropped.length);
  if (run.scenario.drop_every) vars.every = String(run.scenario.drop_every.every);
  if (run.scenario.freeze) {
    vars.freezeStart = String(run.scenario.freeze.start_frame);
    vars.freezeEnd = String(run.scenario.freeze.end_frame);
  }
  return vars;
}
