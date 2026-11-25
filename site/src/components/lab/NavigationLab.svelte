<script lang="ts">
  import { onMount, tick } from 'svelte';
  import type { Dict } from '../../i18n/en';
  import { createScene, type NavScene } from '../../lib/navigation/scene';
  import type { NavigationDoc, VoRun } from '../../lib/navigation/types';
  import { fill } from '../../lib/format';

  interface Props {
    t: Dict['navigation'];
  }

  let { t }: Props = $props();

  type RunName = 'base' | 'blur';
  const url = (path: string) => `${import.meta.env.BASE_URL.replace(/\/?$/, '/')}${path}`;

  let root: HTMLElement;
  let canvas = $state() as HTMLCanvasElement;
  let doc = $state.raw<NavigationDoc | null>(null);
  let error = $state<string | null>(null);
  let name = $state<RunName>('base');
  let index = $state(0);
  let playing = $state(false);
  let scene: NavScene | null = null;
  let lastTs = 0;
  // playback time, s: kept apart from the pose time, or a display frame shorter than one pose interval is lost
  let clock = 0;

  const run = $derived<VoRun | null>(doc ? doc.runs[name] : null);
  const pose = $derived(run ? run.poses[Math.min(index, run.poses.length - 1)]! : null);
  const total = $derived(run ? run.poses.at(-1)![0] : 0);

  // thumbnail of the nearest frame in the atlas
  const thumb = $derived.by(() => {
    if (!run || !pose) return null;
    const a = run.atlas;
    const k = Math.min(a.count - 1, Math.round(pose[11] / a.every));
    const [w, h] = a.size;
    const rows = Math.ceil(a.count / a.cols);
    return {
      image: url(a.image),
      x: (k % a.cols) * w,
      y: Math.floor(k / a.cols) * h,
      size: `${a.cols * w}px ${rows * h}px`,
      w,
      h,
    };
  });

  // error-over-time chart, SVG units
  const CW = 600, CH = 120, CL = 36, CR = 8, CT = 8, CB = 20;
  const chart = $derived.by(() => {
    if (!run) return null;
    // the axis ends at the next 0.05 m above the largest error, ticks every 0.05 m
    const maxErr = Math.ceil(Math.max(...run.poses.map((p) => p[8])) * 20) / 20;
    const ticks = Array.from({ length: Math.round(maxErr * 20) + 1 }, (_, k) => k * 0.05);
    const x = (s: number) => CL + (s / total) * (CW - CL - CR);
    const y = (e: number) => CT + (1 - e / maxErr) * (CH - CT - CB);
    const degraded = run.poses.filter((p) => run.statuses[p[9]] === 'DEGRADED').map((p) => x(p[0]));
    return {
      ticks,
      path: run.poses.map((p, i) => `${i ? 'L' : 'M'}${x(p[0]).toFixed(1)},${y(p[8]).toFixed(1)}`).join(''),
      degraded,
      x,
      y,
    };
  });

  function css(token: string): string {
    return getComputedStyle(root).getPropertyValue(token).trim();
  }

  function pick(n: RunName): void {
    name = n;
    if (doc) scene?.showRun(doc.runs[n]);
  }

  function seek(i: number): void {
    index = i;
    scene?.showPose(i);
  }

  function step(ts: number): void {
    if (!playing || !run) return;
    if (lastTs) {
      clock += (ts - lastTs) / 1000;
      if (clock > total) clock = 0;
      let i = clock < run.poses[index]![0] ? 0 : index;
      while (i < run.poses.length - 1 && run.poses[i + 1]![0] <= clock) i += 1;
      if (i !== index) seek(i);
    }
    lastTs = ts;
    requestAnimationFrame(step);
  }

  function toggle(): void {
    playing = !playing;
    lastTs = 0;
    if (!playing || !run) return;
    clock = run.poses[index]![0];
    requestAnimationFrame(step);
  }

  function scrub(e: PointerEvent): void {
    if (!run || !chart || e.buttons === 0) return;
    const svg = e.currentTarget as SVGSVGElement;
    const r = svg.getBoundingClientRect();
    const s = (((e.clientX - r.left) / r.width) * CW - CL) / (CW - CL - CR) * total;
    let i = 0;
    while (i < run.poses.length - 1 && run.poses[i + 1]![0] <= s) i += 1;
    playing = false;
    seek(i);
  }

  onMount(() => {
    const ro = new ResizeObserver(() => scene?.resize());
    (async () => {
      const r = await fetch(url('data/navigation.json'));
      if (!r.ok) throw new Error(`data/navigation.json: HTTP ${r.status}`);
      doc = (await r.json()) as NavigationDoc;
      await tick();
      scene = createScene(canvas, doc, {
        gt: css('--fg'),
        vo: css('--accent'),
        degraded: css('--drop'),
        lost: css('--frozen'),
        error: css('--frozen'),
        grid: css('--line'),
        camera: css('--accent'),
      });
      scene.showRun(doc.runs[name]);
      ro.observe(canvas);
    })().catch((e: unknown) => (error = fill(t.loadError, { error: e instanceof Error ? e.message : String(e) })));
    return () => {
      playing = false;
      ro.disconnect();
      scene?.dispose();
    };
  });
</script>

<div class="nav" bind:this={root}>
  {#if error}
    <p class="note">{error}</p>
  {:else if !doc}
    <p class="note">{t.loading}</p>
  {/if}
  <div class="grid" hidden={!doc}>
    <div class="view">
      <div class="seg" role="group" aria-label={t.title}>
        {#each ['base', 'blur'] as const as n (n)}
          <button aria-pressed={name === n} onclick={() => pick(n)}>
            {n === 'base' ? t.runs.base : fill(t.runs.blur, { length: doc?.runs.blur.degradation?.length_px ?? '' })}
          </button>
        {/each}
      </div>
      <div class="stage">
        <canvas bind:this={canvas} aria-label={t.drag}></canvas>
      </div>
      <div class="legend">
        <span><i style:background="var(--fg)"></i>{t.legend.gt}</span>
        <span><i style:background="var(--accent)"></i>{t.legend.vo}</span>
        <span><i style:background="var(--drop)"></i>{t.legend.degraded}</span>
        <span><i style:background="var(--frozen)"></i>{t.legend.error}</span>
        <span class="drag">{t.drag}</span>
      </div>
      {#if run && chart && pose}
        <div class="timeline">
          <button class="play" onclick={toggle} aria-label={playing ? t.pause : t.play}>
            <svg viewBox="0 0 16 16" aria-hidden="true">
              {#if playing}<path d="M3 2h4v12H3zM9 2h4v12H9z" />{:else}<path d="M3 2l11 6-11 6z" />{/if}
            </svg>
          </button>
          <input
            type="range"
            min="0"
            max={run.poses.length - 1}
            value={index}
            aria-label={t.time}
            oninput={(e) => {
              playing = false;
              seek(Number((e.currentTarget as HTMLInputElement).value));
            }}
          />
        </div>
        <div class="card">
          <h3>{t.chart.title}, {t.chart.unit}</h3>
          <svg
            class="chart"
            viewBox="0 0 {CW} {CH}"
            role="img"
            aria-label={t.chart.title}
            onpointerdown={scrub}
            onpointermove={scrub}
          >
            {#each chart.ticks as v (v)}
              <line x1={CL} x2={CW - CR} y1={chart.y(v)} y2={chart.y(v)} class="grid-line" />
              <text x={CL - 4} y={chart.y(v) + 3} text-anchor="end">{v.toFixed(2)}</text>
            {/each}
            {#each chart.degraded as dx, k (k)}
              <line x1={dx} x2={dx} y1={CT} y2={CH - CB} class="degraded" />
            {/each}
            <path d={chart.path} class="err" />
            <line x1={chart.x(pose[0])} x2={chart.x(pose[0])} y1={CT} y2={CH - CB} class="cursor" />
            {#each [0, Math.round(total / 2), Math.floor(total)] as s (s)}
              <text x={chart.x(s)} y={CH - 6} text-anchor="middle">{s} {t.units.s}</text>
            {/each}
          </svg>
          {#if chart.degraded.length}<p class="note"><i class="swatch"></i>{t.chart.degraded}</p>{/if}
        </div>
      {/if}
    </div>

    <aside class="side">
      {#if run && pose && thumb}
        <div class="card">
          <h3>{t.point.title}</h3>
          <div
            class="thumb"
            style:width="{thumb.w}px"
            style:height="{thumb.h}px"
            style:background-image="url({thumb.image})"
            style:background-position="-{thumb.x}px -{thumb.y}px"
            style:background-size={thumb.size}
          ></div>
          <p class="note">{run.degradation ? t.frameNoteBlur : t.frameNote}</p>
          <dl>
            <div><dt>{t.time}</dt><dd>{fill(t.point.time, { t: pose[0].toFixed(2), total: total.toFixed(1) })}</dd></div>
            <div><dt>{t.point.status}</dt><dd class:degraded={run.statuses[pose[9]] === 'DEGRADED'}>{run.statuses[pose[9]]}</dd></div>
            <div><dt>{t.point.inliers}</dt><dd>{pose[10]}</dd></div>
            <div><dt>{t.point.error}</dt><dd class="bad">{fill(t.point.errorValue, { v: (pose[8] * 100).toFixed(1) })}</dd></div>
          </dl>
        </div>
        <div class="card">
          <h3>{t.stats.title}</h3>
          <dl>
            <div>
              <dt>{t.stats.ate}</dt>
              <dd>{run.ate_m.rmse} {t.units.m}</dd>
            </div>
            <div>
              <dt></dt>
              <dd class="small">{t.stats.median} {run.ate_m.median} · {t.stats.max} {run.ate_m.max}</dd>
            </div>
            <div><dt>{t.stats.path}</dt><dd>{doc!.gt_path_length_m} {t.units.m}</dd></div>
            {#each run.rpe as r (r.delta + r.unit)}
              <div>
                <dt>{fill(t.stats.rpe, { delta: r.delta, unit: t.units[r.unit] })}</dt>
                <dd class="small">{fill(t.stats.rpeValue, { rmse: r.trans_rmse_m, rot: r.rot_mean_deg })}</dd>
              </div>
            {/each}
            <div>
              <dt>{t.stats.statuses}</dt>
              <dd class="small">
                {Object.entries(run.status_counts).map(([k, v]) => `${k} ${v}`).join(' · ')}
              </dd>
            </div>
            <div><dt>{t.stats.inliers}</dt><dd>{run.median_inliers}</dd></div>
          </dl>
          <p class="note">
            {fill(t.stats.alignment, {
              alignment: doc!.alignment,
              matched: run.poses.length,
              total: doc!.estimated_poses,
              dt: doc!.association_max_difference_s,
            })}
          </p>
          <p class="src mono">{fill(t.source, { run: run.run })}</p>
        </div>
      {/if}
    </aside>
  </div>
</div>

<style>
  .grid {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 330px;
    gap: 14px;
    align-items: start;
  }

  .grid[hidden] {
    display: none;
  }

  .view,
  .side {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    gap: 10px;
    min-width: 0;
  }

  .stage {
    aspect-ratio: 16 / 10;
    overflow: hidden;
    border: 1px solid var(--line);
    border-radius: var(--radius);
    background: var(--panel-2);
  }

  canvas {
    display: block;
    width: 100%;
    height: 100%;
    touch-action: none;
  }

  .card {
    padding: 12px 14px;
    border: 1px solid var(--line);
    border-radius: var(--radius);
    background: var(--panel);
  }

  h3 {
    margin-bottom: 10px;
    font-family: var(--f-mono);
    font-size: 13px;
    font-weight: 500;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--muted);
  }

  .note {
    margin: 6px 0 0;
    font-size: 12.5px;
    color: var(--muted);
  }

  .src {
    margin: 6px 0 0;
    font-size: 12px;
    color: var(--faint);
    overflow-wrap: anywhere;
  }

  .seg {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }

  button {
    padding: 5px 10px;
    border: 1px solid var(--line);
    border-radius: var(--radius);
    background: var(--panel-2);
    color: var(--fg);
    font-size: 13px;
    cursor: pointer;
  }

  button[aria-pressed='true'] {
    border-color: var(--accent);
  }

  .legend {
    display: flex;
    flex-wrap: wrap;
    gap: 4px 14px;
    font-size: 12.5px;
    color: var(--muted);
  }

  .legend i,
  .swatch {
    display: inline-block;
    width: 10px;
    height: 10px;
    margin-right: 6px;
    border-radius: 2px;
    vertical-align: -1px;
  }

  .swatch {
    background: var(--drop);
  }

  .drag {
    margin-left: auto;
  }

  .timeline {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .play {
    display: inline-grid;
    place-items: center;
    width: 36px;
    height: 32px;
    padding: 0;
  }

  .play svg {
    width: 14px;
    height: 14px;
    fill: currentColor;
  }

  .timeline input {
    flex: 1;
    accent-color: var(--accent);
  }

  .chart {
    display: block;
    width: 100%;
    height: auto;
    font-family: var(--f-mono);
    font-size: 10px;
    cursor: ew-resize;
    touch-action: none;
  }

  .chart text {
    fill: var(--faint);
  }

  .grid-line {
    stroke: var(--line);
  }

  .degraded {
    stroke: var(--drop);
    stroke-width: 2;
    opacity: 0.6;
  }

  .err {
    fill: none;
    stroke: var(--frozen);
    stroke-width: 1.5;
  }

  .cursor {
    stroke: var(--accent);
    stroke-width: 2;
  }

  .thumb {
    max-width: 100%;
    border: 1px solid var(--line);
    border-radius: 2px;
    background-repeat: no-repeat;
  }

  dl {
    display: grid;
    gap: 6px;
    margin: 10px 0 0;
  }

  dl div {
    display: flex;
    justify-content: space-between;
    gap: 10px;
    font-size: 13px;
  }

  dt {
    color: var(--muted);
  }

  dd {
    margin: 0;
    font-family: var(--f-mono);
    font-variant-numeric: tabular-nums;
    text-align: right;
  }

  dd.small {
    font-size: 12px;
    color: var(--muted);
  }

  dd.bad {
    color: var(--frozen);
  }

  dd.degraded {
    color: var(--drop);
  }

  @media (max-width: 980px) {
    .grid {
      grid-template-columns: minmax(0, 1fr);
    }

    .drag {
      margin-left: 0;
    }
  }
</style>
