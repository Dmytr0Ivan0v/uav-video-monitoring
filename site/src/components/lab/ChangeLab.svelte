<script lang="ts">
  import { onMount } from 'svelte';
  import type { Dict } from '../../i18n/en';
  import type { ChangeDoc } from '../../lib/change/types';
  import { fill } from '../../lib/format';

  interface Props {
    t: Dict['change'];
  }

  let { t }: Props = $props();

  const url = (path: string) => `${import.meta.env.BASE_URL.replace(/\/?$/, '/')}${path}`;

  let canvas = $state() as HTMLCanvasElement;
  let doc = $state.raw<ChangeDoc | null>(null);
  let error = $state<string | null>(null);
  let mediaOk = $state(true);
  let pairIndex = $state(0);
  let k = $state(0); // index into taus
  let split = $state(50); // curtain, percent from the left
  let showMask = $state(true);

  let images: { t0: HTMLImageElement; t1: HTMLImageElement; levels: ImageData } | null = null;
  let overlay: OffscreenCanvas | null = null;

  const pair = $derived(doc ? doc.shown[pairIndex]! : null);
  const tau = $derived(doc ? doc.taus[k]! : 0);
  const row = $derived(doc && pair ? doc.metrics[pair.id]?.find((m) => m.tau === tau) : undefined);
  const point = $derived(doc?.pr_curve.find((p) => p.tau === tau));
  const best = $derived(doc ? doc.pr_curve.reduce((a, b) => (b.f1 > a.f1 ? b : a)) : null);
  const reviewed = $derived(doc ? Object.values(doc.fp_review.counts).reduce((a, b) => a + b, 0) : 0);

  // PR chart, SVG units
  const W = 320, H = 220, L = 40, R = 12, T = 12, B = 32;
  const x = (recall: number) => L + recall * (W - L - R);
  const y = (precision: number) => T + (1 - precision) * (H - T - B);

  function loadImage(path: string): Promise<HTMLImageElement> {
    return new Promise((resolve, reject) => {
      const img = new Image();
      img.onload = () => resolve(img);
      img.onerror = () => reject(new Error(path));
      img.src = url(path);
    });
  }

  async function loadLevels(path: string): Promise<ImageData> {
    const r = await fetch(url(path));
    if (!r.ok) throw new Error(`${path}: HTTP ${r.status}`);
    const bitmap = await createImageBitmap(await r.blob(), { colorSpaceConversion: 'none', premultiplyAlpha: 'none' });
    const c = new OffscreenCanvas(bitmap.width, bitmap.height);
    const ctx = c.getContext('2d')!;
    ctx.drawImage(bitmap, 0, 0);
    return ctx.getImageData(0, 0, bitmap.width, bitmap.height);
  }

  async function loadPair(i: number): Promise<void> {
    if (!doc) return;
    pairIndex = i;
    const p = doc.shown[i]!;
    try {
      const [t0, t1, levels] = await Promise.all([loadImage(p.image_t0), loadImage(p.image_t1), loadLevels(p.levels)]);
      if (pairIndex !== i) return;
      images = { t0, t1, levels };
      buildOverlay();
      draw();
    } catch {
      mediaOk = false;
    }
  }

  // the mask at taus[k]: a pixel is in it when its level is above k
  function buildOverlay(): void {
    if (!images) return;
    const { levels } = images;
    overlay = new OffscreenCanvas(levels.width, levels.height);
    const out = new ImageData(levels.width, levels.height);
    for (let i = 0; i < levels.data.length; i += 4) {
      if (levels.data[i]! > k) {
        out.data[i] = 239;
        out.data[i + 1] = 91;
        out.data[i + 2] = 87;
        out.data[i + 3] = 170;
      }
    }
    overlay.getContext('2d')!.putImageData(out, 0, 0);
  }

  function draw(): void {
    if (!images) return;
    const { t0, t1 } = images;
    canvas.width = t1.naturalWidth;
    canvas.height = t1.naturalHeight;
    const ctx = canvas.getContext('2d')!;
    const w = canvas.width, h = canvas.height;
    const sx = (split / 100) * w;
    ctx.drawImage(t1, 0, 0, w, h);
    ctx.save();
    ctx.beginPath();
    ctx.rect(0, 0, sx, h);
    ctx.clip();
    ctx.drawImage(t0, 0, 0, w, h);
    ctx.restore();
    if (showMask && overlay) ctx.drawImage(overlay, 0, 0, w, h);
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(sx - 1, 0, 2, h);
  }

  onMount(() => {
    (async () => {
      const r = await fetch(url('data/change.json'));
      if (!r.ok) throw new Error(`data/change.json: HTTP ${r.status}`);
      doc = (await r.json()) as ChangeDoc;
      k = doc.taus.indexOf(doc.tau);
      await loadPair(0);
    })().catch((e: unknown) => (error = fill(t.loadError, { error: e instanceof Error ? e.message : String(e) })));
  });
</script>

<div class="lab">
  {#if error}
    <p class="note">{error}</p>
  {:else if !doc}
    <p class="note">{t.loading}</p>
  {:else}
    <div class="grid">
      <div class="view">
        <div class="seg" role="group" aria-label={t.title}>
          {#each doc.shown as p, i (p.id)}
            <button aria-pressed={pairIndex === i} onclick={() => loadPair(i)}>
              <span class="mono">{p.id}</span> · {t.pairs[p.kind]}
            </button>
          {/each}
        </div>
        {#if pair}
          <p class="note mono">
            {pair.t1 == null
              ? fill(t.pairSynthetic, { id: pair.id, t0: pair.t0 })
              : fill(t.pair, { id: pair.id, t0: pair.t0, t1: pair.t1 })} · {fill(t.inliers, { n: pair.inliers })}
          </p>
        {/if}
        {#if mediaOk}
          <div class="frame" style:aspect-ratio={pair ? `${pair.size[0]} / ${pair.size[1]}` : '16 / 9'}>
            <canvas bind:this={canvas}></canvas>
          </div>
          <label class="slider">
            <span>{t.curtain}</span>
            <input type="range" min="0" max="100" bind:value={split} oninput={draw} />
          </label>
          <label class="check"><input type="checkbox" bind:checked={showMask} onchange={draw} /> {t.showMask}</label>
        {:else}
          <p class="note">{t.noMedia}</p>
        {/if}
        <label class="slider">
          <span class="mono">
            {fill(t.tau, { tau })}{#if tau === doc.tau}{' · '}<span class="working">{t.working}</span>{/if}
          </span>
          <input
            type="range"
            min="0"
            max={doc.taus.length - 1}
            bind:value={k}
            oninput={() => {
              buildOverlay();
              draw();
            }}
          />
        </label>
      </div>

      <aside class="side">
        {#if pair && row}
          <div class="card">
            <h3>{fill(t.stats.title, { tau })}</h3>
            <dl>
              {#if row.n_changed > 0}
                <div><dt>{t.stats.found}</dt><dd>{row.n_found} / {row.n_changed}</dd></div>
              {/if}
              <div><dt>{t.stats.false}</dt><dd class="bad">{row.n_false_comp}</dd></div>
              <div>
                <dt>{t.stats.share}</dt>
                <dd>{((row.mask_px / (pair.size[0] * pair.size[1])) * 100).toFixed(2)}%</dd>
              </div>
            </dl>
            {#if row.n_changed === 0}<p class="note">{t.stats.none}</p>{/if}
          </div>
        {/if}

        <div class="card">
          <h3>{t.curve.title}</h3>
          <svg viewBox="0 0 {W} {H}" role="img" aria-label={t.curve.title}>
            {#each [0, 0.25, 0.5, 0.75, 1] as v (v)}
              <line x1={L} x2={W - R} y1={y(v)} y2={y(v)} class="grid-line" />
              <line x1={x(v)} x2={x(v)} y1={T} y2={H - B} class="grid-line" />
              <text x={L - 5} y={y(v) + 3} text-anchor="end">{v}</text>
              <text x={x(v)} y={H - B + 13} text-anchor="middle">{v}</text>
            {/each}
            <text x={W - R} y={H - 3} text-anchor="end">{t.curve.recall}</text>
            <text x={L} y={T - 2}>{t.curve.precision}</text>
            <polyline points={doc.pr_curve.map((p) => `${x(p.recall)},${y(p.precision)}`).join(' ')} class="curve" />
            {#each doc.pr_curve as p (p.tau)}
              <circle cx={x(p.recall)} cy={y(p.precision)} r={p.tau === tau ? 6 : 2.5} class:now={p.tau === tau} />
            {/each}
          </svg>
          {#if point}
            <p class="note mono">
              τ {point.tau}: P {point.precision} · R {point.recall} · F1 {point.f1} ·
              {fill(t.curve.falsePerPair, { n: point.false_comp_per_pair })}
            </p>
          {/if}
          {#if best}<p class="note mono">{fill(t.curve.best, { f1: best.f1, tau: best.tau })}</p>{/if}
          <p class="note">
            {fill(t.curve.text, {
              n: doc.pr_curve[0]!.n_pairs,
              iou: doc.proxy.changed_iou,
              cover: `${doc.proxy.recall_cover * 100}%`,
            })}
          </p>
        </div>
      </aside>
    </div>

    <div class="below">
      <section class="card">
        <h3>{t.light.title}</h3>
        <p class="note">{t.light.text}</p>
        <table>
          <thead>
            <tr><th>{t.light.pair}</th><th class="n">{t.light.with}</th><th class="n">{t.light.without}</th></tr>
          </thead>
          <tbody>
            {#each doc.light as l (l.pair)}
              <tr>
                <td class="mono">{l.pair}</td>
                <td class="n">{l.false_events}</td>
                <td class="n bad">{l.false_events_no_normalization}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </section>

      <section class="card">
        <h3>{t.review.title}</h3>
        <p class="note">{fill(t.review.text, { n: reviewed })}</p>
        <ul class="counts">
          {#each Object.entries(doc.fp_review.counts) as [cls, n] (cls)}
            <li><span>{t.review.classes[cls as keyof typeof t.review.classes] ?? cls}</span><b class="mono">{n}</b></li>
          {/each}
        </ul>
        {#if mediaOk}
          <div class="examples">
            {#each doc.examples as e (e.image)}
              <figure>
                <img src={url(e.image)} alt="" loading="lazy" />
                <figcaption class="mono">
                  {e.pair} · {t.review.kinds[e.kind]}{#if e.label} · {t.review.classes[e.label as keyof typeof t.review.classes] ?? e.label}{/if}
                </figcaption>
              </figure>
            {/each}
          </div>
          <p class="note">{t.review.crops}</p>
        {/if}
      </section>
    </div>
    <p class="src mono">{fill(t.source, { run: doc.run })}</p>
  {/if}
</div>

<style>
  .grid {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 330px;
    gap: 14px;
    align-items: start;
  }

  .view,
  .side {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    gap: 10px;
    min-width: 0;
  }

  .frame {
    overflow: hidden;
    border: 1px solid var(--line);
    border-radius: var(--radius);
    background: var(--panel-2);
  }

  canvas {
    display: block;
    width: 100%;
    height: 100%;
  }

  .below {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(0, 2fr);
    gap: 14px;
    margin-top: 14px;
    align-items: start;
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
    margin: 14px 0 0;
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

  .slider {
    display: grid;
    gap: 2px;
    font-size: 13px;
    color: var(--muted);
  }

  .slider input {
    width: 100%;
    accent-color: var(--accent);
  }

  .working {
    color: var(--accent);
  }

  .check {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 13px;
  }

  .check input {
    accent-color: var(--accent);
  }

  dl {
    display: grid;
    gap: 6px;
    margin: 0;
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
  }

  .bad {
    color: var(--frozen);
  }

  svg {
    display: block;
    width: 100%;
    height: auto;
    font-family: var(--f-mono);
    font-size: 10px;
  }

  svg text {
    fill: var(--faint);
  }

  .grid-line {
    stroke: var(--line);
  }

  .curve {
    fill: none;
    stroke: var(--accent);
    stroke-width: 1.5;
  }

  circle {
    fill: var(--accent);
  }

  circle.now {
    fill: none;
    stroke: var(--fg);
    stroke-width: 2;
  }

  table {
    width: 100%;
    margin-top: 8px;
    border-collapse: collapse;
    font-size: 13px;
  }

  th,
  td {
    padding: 6px 10px 6px 0;
    border-bottom: 1px solid var(--line);
    text-align: left;
  }

  th {
    font-family: var(--f-mono);
    font-size: 11.5px;
    font-weight: 500;
    color: var(--muted);
  }

  .n {
    font-family: var(--f-mono);
    font-variant-numeric: tabular-nums;
    text-align: right;
  }

  .counts {
    display: flex;
    flex-wrap: wrap;
    gap: 6px 16px;
    margin: 8px 0 0;
    padding: 0;
    list-style: none;
    font-size: 13px;
    color: var(--muted);
  }

  .counts b {
    margin-left: 6px;
    font-weight: 500;
    color: var(--fg);
  }

  .examples {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(min(100%, 260px), 1fr));
    gap: 10px;
    margin-top: 10px;
  }

  figure {
    margin: 0;
  }

  figure img {
    display: block;
    width: 100%;
    height: auto;
    border: 1px solid var(--line);
    border-radius: 2px;
  }

  figcaption {
    margin-top: 4px;
    font-size: 11.5px;
    color: var(--muted);
  }

  @media (max-width: 980px) {
    .grid,
    .below {
      grid-template-columns: minmax(0, 1fr);
    }
  }
</style>
