<script lang="ts">
  import { onMount } from 'svelte';
  import type { Dict } from '../../i18n/en';
  import { GROUPS, groupIndex } from '../../lib/console/classes';
  import { readColors, type Colors } from '../../lib/console/colors';
  import { compare, type Comparison } from '../../lib/detector/compare';
  import { decode } from '../../lib/detector/decode';
  import { degrade } from '../../lib/detector/degrade';
  import { letterbox, toTensor } from '../../lib/detector/preprocess';
  import { createSession, fetchModel, webgpuAvailable, type Session } from '../../lib/detector/session';
  import type { Backend, Box, DegradationType, DetectorDoc, Picture } from '../../lib/detector/types';
  import { fill } from '../../lib/format';
  import Curve from './Curve.svelte';

  interface Props {
    t: Dict['lab'];
    groups: Dict['console']['groups'];
    clip: string;
  }

  let { t, groups, clip }: Props = $props();

  const TYPES: DegradationType[] = ['blur', 'noise', 'low_light', 'jpeg'];
  const url = (path: string) => `${import.meta.env.BASE_URL.replace(/\/?$/, '/')}${path}`;

  let root: HTMLElement;
  let canvas = $state() as HTMLCanvasElement;
  let colors = $state.raw<Colors | null>(null);
  let doc = $state.raw<DetectorDoc | null>(null);
  let loadError = $state<string | null>(null);

  let gpu = $state(false);
  let backend = $state<Backend>('wasm');
  let status = $state<'idle' | 'loading' | 'starting' | 'ready' | 'error'>('idle');
  let loadedBytes = $state(0);
  let modelError = $state('');
  let modelBytes: Uint8Array | null = null;
  let session: Session | null = null;

  let framesOk = $state(true);
  let selectedFrame = $state<number | null>(null);
  let original = $state.raw<Picture | null>(null);
  let pictureSeed = 0;

  let dType = $state<DegradationType | null>(null);
  let dLevel = $state(1);
  let conf = $state(0.1);
  let iou = $state(0.7);

  let busy = $state(false);
  let result = $state.raw<{ boxes: Box[]; ms: { d: number; p: number; i: number; n: number }; first: boolean } | null>(
    null,
  );
  let runs = 0;

  let checks = $state.raw<{ frame: number; cmp: Comparison }[]>([]);
  let checking = $state<number | null>(null);

  const mb = (bytes: number) => (bytes / 1_000_000).toFixed(1);
  const threads = $derived(
    typeof globalThis.crossOriginIsolated === 'boolean' && globalThis.crossOriginIsolated
      ? Math.min(4, navigator.hardwareConcurrency || 1)
      : 1,
  );
  const levelValue = $derived(dType && doc ? doc.degradations.types[dType].levels[dLevel] ?? null : null);
  const tolerance = $derived(
    doc && {
      iouMin: doc.browser_tolerance.iou_min,
      maxScoreDiff: doc.browser_tolerance.max_score_diff[backend],
      nearThreshold: doc.browser_tolerance.near_threshold,
    },
  );
  const counts = $derived.by(() => {
    const c = GROUPS.map(() => 0);
    for (const b of result?.boxes ?? []) c[groupIndex(b[0])]! += 1;
    return c;
  });

  async function loadPicture(path: string): Promise<Picture> {
    const r = await fetch(url(path));
    if (!r.ok) throw new Error(`${path}: HTTP ${r.status}`);
    return pictureOf(await r.blob());
  }

  async function pictureOf(blob: Blob): Promise<Picture> {
    // no colour management: the PNG pixels must reach the model as Python read them
    const bitmap = await createImageBitmap(blob, { colorSpaceConversion: 'none', premultiplyAlpha: 'none' });
    const c = new OffscreenCanvas(bitmap.width, bitmap.height);
    const ctx = c.getContext('2d')!;
    ctx.drawImage(bitmap, 0, 0);
    return ctx.getImageData(0, 0, bitmap.width, bitmap.height);
  }

  async function startSession(): Promise<void> {
    if (!modelBytes) return;
    status = 'starting';
    session = await createSession(modelBytes, backend);
    status = 'ready';
  }

  async function loadModel(): Promise<void> {
    if (!doc) return;
    try {
      status = 'loading';
      modelBytes = await fetchModel(url(doc.model.path), (done) => (loadedBytes = done));
      await startSession();
      runs = 0;
      if (original) await detect();
    } catch (e) {
      status = 'error';
      modelError = e instanceof Error ? e.message : String(e);
    }
  }

  async function switchBackend(b: Backend): Promise<void> {
    backend = b;
    checks = [];
    if (!modelBytes) return;
    try {
      await startSession();
      runs = 0;
      if (original) await detect();
    } catch (e) {
      status = 'error';
      modelError = e instanceof Error ? e.message : String(e);
    }
  }

  async function run(picture: Picture, c: number, i: number) {
    const d = doc!;
    const t1 = performance.now();
    const { rgb, lb } = letterbox(picture, [d.model.input[2], d.model.input[3]]);
    const tensor = toTensor(rgb, lb.shape);
    const t2 = performance.now();
    const out = await session!.run(tensor, d.model.input);
    const t3 = performance.now();
    const boxes = decode(out, d.model.output[2], lb, [picture.height, picture.width], {
      conf: c,
      iou: i,
      maxDet: d.inference.max_det,
      classes: d.inference.classes,
    });
    return { boxes, p: t2 - t1, i: t3 - t2, n: performance.now() - t3 };
  }

  async function detect(): Promise<void> {
    if (!session || !original || !doc || busy) return;
    busy = true;
    try {
      const t0 = performance.now();
      const picture = await degrade(original, dType, levelValue, doc.degradations.seed * 1000 + pictureSeed);
      const d = performance.now() - t0;
      const r = await run(picture, conf, iou);
      result = { boxes: r.boxes, ms: { d, p: r.p, i: r.i, n: r.n }, first: runs === 0 && backend === 'webgpu' };
      runs += 1;
      draw(picture, r.boxes);
    } finally {
      busy = false;
    }
  }

  function draw(picture: Picture, boxes: Box[]): void {
    canvas.width = picture.width;
    canvas.height = picture.height;
    const ctx = canvas.getContext('2d')!;
    ctx.putImageData(new ImageData(new Uint8ClampedArray(picture.data), picture.width, picture.height), 0, 0);
    ctx.lineWidth = Math.max(1.5, picture.width / 600);
    for (const [cls, , x1, y1, x2, y2] of boxes) {
      ctx.strokeStyle = colors!.groups[groupIndex(cls)]!;
      ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);
    }
  }

  async function pickFrame(i: number): Promise<void> {
    if (!doc) return;
    const ref = doc.references[i]!;
    selectedFrame = i;
    original = await loadPicture(ref.image);
    pictureSeed = ref.frame;
    await detect();
  }

  async function pickOwn(e: Event): Promise<void> {
    const file = (e.currentTarget as HTMLInputElement).files?.[0];
    if (!file) return;
    selectedFrame = null;
    original = await pictureOf(file);
    pictureSeed = 0;
    await detect();
  }

  async function check(): Promise<void> {
    if (!doc || !session || !tolerance) return;
    checks = [];
    for (const ref of doc.references) {
      checking = ref.frame;
      const r = await run(await loadPicture(ref.image), doc.inference.conf, doc.inference.iou);
      checks = [...checks, { frame: ref.frame, cmp: compare(ref.boxes, r.boxes, tolerance) }];
    }
    checking = null;
  }

  onMount(() => {
    colors = readColors(root);
    (async () => {
      const r = await fetch(url('data/detector.json'));
      if (!r.ok) throw new Error(`data/detector.json: HTTP ${r.status}`);
      doc = (await r.json()) as DetectorDoc;
      conf = doc.inference.conf;
      iou = doc.inference.iou;
      gpu = await webgpuAvailable();
      backend = gpu ? 'webgpu' : 'wasm';
      // the example frames are VisDrone pixels, built locally and not always deployed
      framesOk = (await fetch(url(doc.references[0]!.image), { method: 'HEAD' })).ok;
    })().catch((e: unknown) => (loadError = e instanceof Error ? e.message : String(e)));
  });
</script>

<div class="lab" bind:this={root}>
  {#if loadError}
    <p class="msg">{loadError}</p>
  {:else if doc}
    <div class="grid">
      <div class="view">
        <div class="frame" style:aspect-ratio={original ? `${original.width} / ${original.height}` : '16 / 9'}>
          <canvas bind:this={canvas} hidden={!result}></canvas>
        </div>
        {#if result}
          <p class="stats mono">
            {fill(t.result.boxes, { n: result.boxes.length })} ·
            {fill(t.result.timings, {
              d: result.ms.d.toFixed(0),
              p: result.ms.p.toFixed(0),
              i: result.ms.i.toFixed(0),
              n: result.ms.n.toFixed(0),
            })}
          </p>
          {#if result.first}<p class="note">{t.result.first}</p>{/if}
          <div class="legend">
            {#each GROUPS as g, i (g.key)}
              <span><i style:background="var({g.color})"></i>{groups[g.key]} <b class="mono">{counts[i]}</b></span>
            {/each}
          </div>
        {/if}
        <section class="card curve">
          <h3>{t.curve.title}</h3>
          <p class="note">{t.curve.text}</p>
          <Curve {t} curves={doc.curves} selected={dType ? { type: dType, level: dLevel } : null} />
          <p class="src mono">{t.curve.source}</p>
        </section>
      </div>

      <aside class="controls">
        <div class="card">
          <h3>{t.model.backend}</h3>
          <div class="seg" role="group" aria-label={t.model.backend}>
            {#each ['webgpu', 'wasm'] as const as b (b)}
              <button
                aria-pressed={backend === b}
                disabled={(b === 'webgpu' && !gpu) || status === 'loading' || status === 'starting'}
                onclick={() => switchBackend(b)}>{t.backends[b]}</button
              >
            {/each}
          </div>
          {#if !gpu}<p class="note">{t.model.noWebgpu}</p>{/if}
          {#if backend === 'wasm'}<p class="note mono">{fill(t.model.threads, { n: threads })}</p>{/if}
          {#if status === 'idle' || status === 'error'}
            <button class="primary" onclick={loadModel}>{fill(t.model.load, { mb: mb(doc.model.bytes) })}</button>
          {/if}
          {#if status === 'loading'}
            <p class="mono status">
              {fill(t.model.loading, { done: mb(loadedBytes), total: mb(doc.model.bytes) })}
            </p>
          {:else if status === 'starting'}
            <p class="mono status">{fill(t.model.starting, { backend: t.backends[backend] })}</p>
          {:else if status === 'ready'}
            <p class="mono status ok">{fill(t.model.ready, { backend: t.backends[backend] })}</p>
          {:else if status === 'error'}
            <p class="status bad">{fill(t.model.error, { error: modelError })}</p>
          {/if}
        </div>

        <div class="card">
          <h3>{t.picture.title}</h3>
          {#if framesOk}
            <p class="note">{fill(t.picture.frames, { clip })}</p>
            <div class="thumbs">
              {#each doc.references as ref, i (ref.frame)}
                <button
                  class="thumb"
                  aria-pressed={selectedFrame === i}
                  aria-label={fill(t.picture.frame, { frame: ref.frame })}
                  disabled={status !== 'ready' || busy}
                  onclick={() => pickFrame(i)}
                >
                  <img src={url(ref.image)} alt="" loading="lazy" width="96" height="54" />
                </button>
              {/each}
            </div>
          {:else}
            <p class="note">{t.picture.framesMissing}</p>
          {/if}
          <label class="file">
            <span>{t.picture.own}</span>
            <input type="file" accept="image/*" disabled={status !== 'ready' || busy} onchange={pickOwn} />
          </label>
          <p class="note">{t.picture.ownNote}</p>
        </div>

        <div class="card">
          <h3>{t.distortion.title}</h3>
          <div class="seg many" role="group" aria-label={t.distortion.title}>
            <button aria-pressed={dType == null} onclick={() => ((dType = null), detect())}>{t.distortion.none}</button>
            {#each TYPES as type (type)}
              <button aria-pressed={dType === type} onclick={() => ((dType = type), detect())}>
                {t.distortion.types[type]}
              </button>
            {/each}
          </div>
          {#if dType}
            {@const spec = doc.degradations.types[dType]}
            <div class="seg" role="group" aria-label={t.curve.level}>
              {#each [1, 2, 3] as level (level)}
                <button aria-pressed={dLevel === level} onclick={() => ((dLevel = level), detect())}>
                  {fill(t.distortion.params[spec.param as keyof typeof t.distortion.params], {
                    v: String(spec.levels[level]),
                  })}
                </button>
              {/each}
            </div>
            <p class="note">{t.distortion.notes[dType]}</p>
            <p class="note">{t.distortion.scale}</p>
          {/if}
        </div>

        <div class="card">
          <label class="slider">
            <span class="mono">{fill(t.thresholds.conf, { v: conf.toFixed(2) })}</span>
            <input type="range" min="0.05" max="0.9" step="0.05" bind:value={conf} onchange={detect} />
          </label>
          <label class="slider">
            <span class="mono">{fill(t.thresholds.iou, { v: iou.toFixed(2) })}</span>
            <input type="range" min="0.3" max="0.95" step="0.05" bind:value={iou} onchange={detect} />
          </label>
          <p class="note">{fill(t.thresholds.defaults, { conf: doc.inference.conf, iou: doc.inference.iou })}</p>
        </div>
      </aside>
    </div>

    <div class="below">

      <section class="card">
        <h3>{t.check.title}</h3>
        {#if tolerance}
          <p class="note">
            {fill(t.check.text, {
              n: doc.references.length,
              backend: t.backends[backend],
              iou: tolerance.iouMin,
              ds: tolerance.maxScoreDiff,
              near: tolerance.nearThreshold,
            })}
          </p>
        {/if}
        {#if !framesOk}
          <p class="note">{t.check.needsFrames}</p>
        {:else}
          <button class="primary" disabled={status !== 'ready' || checking != null} onclick={check}>{t.check.run}</button>
          {#if checking != null}<p class="mono status">{fill(t.check.running, { frame: checking })}</p>{/if}
          {#if checks.length}
            <div class="tbl">
              <table>
                <thead>
                  <tr>
                    <th>{t.check.frame}</th>
                    <th class="n">{t.check.python}</th>
                    <th class="n">{t.check.browser}</th>
                    <th class="n">{t.check.pairs}</th>
                    <th class="n">{t.check.ds}</th>
                    <th class="n">{fill(t.check.far, { near: tolerance!.nearThreshold })}</th>
                    <th>{t.check.result}</th>
                  </tr>
                </thead>
                <tbody>
                  {#each checks as c (c.frame)}
                    <tr>
                      <td class="n">{c.frame}</td>
                      <td class="n">{c.cmp.reference}</td>
                      <td class="n">{c.cmp.browser}</td>
                      <td class="n">{c.cmp.pairs}</td>
                      <td class="n">{c.cmp.scoreDiffMax.toFixed(4)}</td>
                      <td class="n">{c.cmp.unmatchedFar}</td>
                      <td class:pass={c.cmp.pass} class:fail={!c.cmp.pass}>{c.cmp.pass ? t.check.pass : t.check.fail}</td>
                    </tr>
                  {/each}
                </tbody>
              </table>
            </div>
            {#if checks.length === doc.references.length}
              <p class="mono status" class:ok={checks.every((c) => c.cmp.pass)} class:bad={!checks.every((c) => c.cmp.pass)}>
                {fill(t.check.summary, {
                  passed: checks.filter((c) => c.cmp.pass).length,
                  total: checks.length,
                  backend: t.backends[backend],
                })}
              </p>
            {/if}
          {/if}
        {/if}
      </section>
    </div>
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
  .controls {
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
    margin-top: 14px;
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

  .note,
  .msg {
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

  .stats {
    margin: 0;
    font-size: 12.5px;
    color: var(--muted);
  }

  .status {
    margin: 8px 0 0;
    font-size: 12.5px;
    color: var(--muted);
  }

  .ok {
    color: var(--ok);
  }

  .bad {
    color: var(--frozen);
  }

  button {
    border: 1px solid var(--line);
    border-radius: var(--radius);
    background: var(--panel-2);
    color: var(--fg);
    font-size: 13px;
    cursor: pointer;
  }

  button:disabled {
    color: var(--faint);
    cursor: default;
  }

  .primary {
    width: 100%;
    margin-top: 10px;
    padding: 9px 14px;
    border-color: var(--accent);
    background: var(--accent);
    color: var(--on-accent);
    font-weight: 600;
  }

  .primary:disabled {
    border-color: var(--line);
    background: var(--panel-2);
  }

  .seg {
    display: flex;
    gap: 6px;
    margin-top: 6px;
  }

  /* not .wrap: base.css uses it for the page container */
  .seg.many {
    flex-wrap: wrap;
  }

  .seg button {
    padding: 5px 10px;
  }

  .seg button[aria-pressed='true'] {
    border-color: var(--accent);
  }

  .thumbs {
    display: grid;
    grid-template-columns: repeat(5, minmax(0, 1fr));
    gap: 6px;
    margin-top: 8px;
  }

  .thumb {
    padding: 0;
    overflow: hidden;
    aspect-ratio: 16 / 9;
  }

  .thumb[aria-pressed='true'] {
    border-color: var(--accent);
    outline: 1px solid var(--accent);
  }

  .thumb img {
    display: block;
    width: 100%;
    height: 100%;
    object-fit: cover;
  }

  .file {
    display: grid;
    gap: 4px;
    margin-top: 12px;
    font-size: 13px;
  }

  .file input {
    max-width: 100%;
    font-size: 12.5px;
  }

  .slider {
    display: grid;
    gap: 2px;
    font-size: 13px;
  }

  .slider + .slider {
    margin-top: 8px;
  }

  .slider input {
    width: 100%;
    accent-color: var(--accent);
  }

  .legend {
    display: flex;
    flex-wrap: wrap;
    gap: 4px 14px;
    font-size: 13px;
  }

  .legend i {
    display: inline-block;
    width: 10px;
    height: 10px;
    margin-right: 6px;
    border-radius: 2px;
    vertical-align: -1px;
  }

  .tbl {
    margin-top: 10px;
    overflow-x: auto;
  }

  table {
    width: 100%;
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
    white-space: nowrap;
  }

  td.pass {
    color: var(--ok);
  }

  td.fail {
    color: var(--frozen);
  }

  @media (max-width: 980px) {
    .grid {
      grid-template-columns: minmax(0, 1fr);
    }

    /* on a phone the model button and the frames come before the empty picture */
    .controls {
      order: -1;
    }
  }
</style>
