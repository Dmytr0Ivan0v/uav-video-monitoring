import { GROUPS } from './classes';

// Canvas cannot read CSS variables, so the tokens are resolved once on mount.
export interface Colors {
  ok: string;
  drop: string;
  frozen: string;
  line: string;
  faint: string;
  fg: string;
  accent: string;
  gt: string;
  decode: string;
  prepost: string;
  inference: string;
  track: string;
  groups: string[];
}

export function readColors(el: Element): Colors {
  const css = getComputedStyle(el);
  const tok = (name: string) => css.getPropertyValue(name).trim();
  return {
    ok: tok('--ok'),
    drop: tok('--drop'),
    frozen: tok('--frozen'),
    line: tok('--line'),
    faint: tok('--faint'),
    fg: tok('--fg'),
    accent: tok('--accent'),
    gt: tok('--gt'),
    decode: tok('--s-decode'),
    prepost: tok('--s-prepost'),
    inference: tok('--s-infer'),
    track: tok('--s-track'),
    groups: GROUPS.map((g) => tok(g.color)),
  };
}
