import { percent } from '../console/checks';
import type { FactsDoc } from './types';

// {name} is the value as exported, {name_pct} the same share as a percent for prose
export function factVars(facts: FactsDoc): Record<string, string> {
  const vars: Record<string, string> = {};
  for (const [name, f] of Object.entries(facts)) {
    vars[name] = String(f.value);
    if (typeof f.value === 'number') vars[`${name}_pct`] = percent(f.value);
  }
  return vars;
}
