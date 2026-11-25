<script lang="ts">
  import type { Dict } from '../../i18n/en';
  import type { DegradationType, DetectorDoc } from '../../lib/detector/types';

  interface Props {
    t: Dict['lab'];
    curves: DetectorDoc['curves'];
    selected: { type: DegradationType; level: number } | null;
  }

  let { t, curves, selected }: Props = $props();

  const TYPES: DegradationType[] = ['blur', 'noise', 'low_light', 'jpeg'];
  const COLORS: Record<DegradationType, string> = {
    blur: 'var(--accent)',
    noise: 'var(--drop)',
    low_light: 'var(--ok)',
    jpeg: 'var(--c-two)',
  };
  const W = 360, H = 190, L = 40, R = 12, T = 12, B = 30;

  const levels = $derived(Math.max(...curves.map((c) => c.level)));
  // the axis ends at the next 0.05 above the best value
  const top = $derived(Math.ceil(Math.max(...curves.map((c) => c['mAP50-95'])) / 0.05) * 0.05);
  const x = (level: number) => L + (level / levels) * (W - L - R);
  const y = (v: number) => T + (1 - v / top) * (H - T - B);
  const ticks = $derived(Array.from({ length: Math.round(top / 0.05) + 1 }, (_, i) => i * 0.05));
  const lines = $derived(
    TYPES.map((type) => ({
      type,
      points: curves.filter((c) => c.type === type).sort((a, b) => a.level - b.level),
    })),
  );
  const mark = $derived(
    selected ? curves.find((c) => c.type === selected.type && c.level === selected.level) : undefined,
  );
</script>

<figure>
  <svg viewBox="0 0 {W} {H}" role="img" aria-label={t.curve.title}>
    {#each ticks as v (v)}
      <line x1={L} x2={W - R} y1={y(v)} y2={y(v)} class="grid" />
      <text x={L - 6} y={y(v) + 3} text-anchor="end">{v.toFixed(2)}</text>
    {/each}
    {#each Array.from({ length: levels + 1 }, (_, i) => i) as level (level)}
      <text x={x(level)} y={H - B + 16} text-anchor="middle">{level}</text>
    {/each}
    <text x={W - R} y={H - 2} text-anchor="end">{t.curve.level}</text>
    {#each lines as l (l.type)}
      <polyline
        points={l.points.map((p) => `${x(p.level)},${y(p['mAP50-95'])}`).join(' ')}
        stroke={COLORS[l.type]}
        class:dim={selected != null && selected.type !== l.type}
      />
    {/each}
    {#if mark}
      <circle cx={x(mark.level)} cy={y(mark['mAP50-95'])} r="6" stroke={COLORS[mark.type]} />
      <text x={x(mark.level)} y={y(mark['mAP50-95']) - 10} text-anchor="middle" class="value">
        {mark['mAP50-95'].toFixed(4)}
      </text>
    {/if}
  </svg>
  <figcaption>
    {#each TYPES as type (type)}
      <span><i style:background={COLORS[type]}></i>{t.distortion.types[type]}</span>
    {/each}
  </figcaption>
</figure>

<style>
  figure {
    margin: 0;
  }

  /* the drawing is laid out for about 360 px; wider, the labels would grow with it */
  svg {
    display: block;
    width: 100%;
    max-width: 520px;
    height: auto;
    font-family: var(--f-mono);
    font-size: 10px;
  }

  text {
    fill: var(--faint);
  }

  text.value {
    fill: var(--fg);
  }

  .grid {
    stroke: var(--line);
  }

  polyline {
    fill: none;
    stroke-width: 2;
  }

  polyline.dim {
    opacity: 0.3;
  }

  circle {
    fill: none;
    stroke-width: 2;
  }

  figcaption {
    display: flex;
    flex-wrap: wrap;
    gap: 4px 14px;
    margin-top: 4px;
    font-size: 12px;
    color: var(--muted);
  }

  figcaption i {
    display: inline-block;
    width: 10px;
    height: 10px;
    margin-right: 5px;
    border-radius: 2px;
    vertical-align: -1px;
  }
</style>
