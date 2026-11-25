// '{n} frames' + { n: '23' } -> '23 frames'; a missing value is an error, not an empty gap
export function fill(template: string, vars: Record<string, string | number>): string {
  return template.replace(/\{(\w+)\}/g, (_, key: string) => {
    const v = vars[key];
    if (v === undefined) throw new Error(`no value for {${key}} in "${template}"`);
    return String(v);
  });
}

// frame index -> 'mm:ss.mmm' from the clip start
export function clock(frame: number, fps: number): string {
  const ms = Math.round((frame / fps) * 1000);
  const s = Math.floor(ms / 1000);
  const mm = String(Math.floor(s / 60)).padStart(2, '0');
  const ss = String(s % 60).padStart(2, '0');
  return `${mm}:${ss}.${String(ms % 1000).padStart(3, '0')}`;
}
