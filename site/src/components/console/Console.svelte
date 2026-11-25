<script lang="ts">
  import { onMount } from 'svelte';
  import type { Dict } from '../../i18n/en';
  import { readColors, type Colors } from '../../lib/console/colors';
  import { buildReplay, stepIndexAt, type Replay } from '../../lib/console/replay';
  import type { RunId } from '../../lib/console/runs';
  import type { ClipDoc, GtBox, GtDoc, RunDoc } from '../../lib/console/types';
  import { fill } from '../../lib/format';
  import EventLog from './EventLog.svelte';
  import LayersCard from './LayersCard.svelte';
  import Picker from './Picker.svelte';
  import Result from './Result.svelte';
  import StatusCard from './StatusCard.svelte';
  import Timeline from './Timeline.svelte';
  import TrackCard from './TrackCard.svelte';
  import Transport from './Transport.svelte';
  import Viewport from './Viewport.svelte';

  interface Props {
    t: Dict['console'];
    lang: string;
    clip: ClipDoc;
  }

  let { t, lang, clip }: Props = $props();

  let root: HTMLElement;
  let video = $state() as HTMLVideoElement;
  let colors = $state.raw<Colors | null>(null);
  let replay = $state.raw<Replay | null>(null);
  // picked in the list; shownId changes together with replay once the run has loaded
  let runId = $state<RunId>('nominal');
  let shownId = $state<RunId>('nominal');
  let frame = $state(0);
  let tick = $state(0);
  let playing = $state(false);
  let rate = $state(0.5);
  let selected = $state<number | null>(null);
  let layers = $state({ boxes: true, trails: true, gt: false });
  let gt = $state.raw<Map<number, GtBox[]> | null>(null);
  let gtMissing = $state(false);
  let hasVideo = $state(false);
  let still = $state.raw<HTMLImageElement | null>(null);
  let error = $state<string | null>(null);

  const stepIndex = $derived(replay ? stepIndexAt(replay.steps, frame) : -1);
  const step = $derived(replay && stepIndex >= 0 ? replay.steps[stepIndex]! : null);
  const totalIndex = $derived(replay ? replay.run.stages.indexOf('total') : -1);

  const runs = new Map<RunId, Replay>();
  const stills = new Map<number, HTMLImageElement | null>();
  // without a video file the clock runs on animation frames
  let virtualTime = 0;
  let lastTs = 0;

  const url = (path: string) => `${import.meta.env.BASE_URL.replace(/\/?$/, '/')}${path}`;

  async function getJson<T>(path: string): Promise<T> {
    const r = await fetch(url(path));
    if (!r.ok) throw new Error(`${path}: HTTP ${r.status}`);
    return (await r.json()) as T;
  }

  function clamp(f: number): number {
    return Math.min(clip.frames - 1, Math.max(0, f));
  }

  function loadImage(path: string): Promise<HTMLImageElement | null> {
    return new Promise((resolve) => {
      const img = new Image();
      img.onload = () => resolve(img);
      img.onerror = () => resolve(null);
      img.src = url(path);
    });
  }

  async function stillFor(run: RunDoc): Promise<HTMLImageElement | null> {
    const start = run.scenario.freeze?.start_frame;
    if (start == null) return null;
    if (!stills.has(start)) {
      const path = clip.media.stills[String(start)];
      stills.set(start, path ? await loadImage(path) : null);
    }
    return stills.get(start) ?? null;
  }

  async function pick(id: RunId): Promise<void> {
    runId = id;
    selected = null;
    let r = runs.get(id);
    if (!r) {
      r = buildReplay(await getJson<RunDoc>(`data/console/${id}.json`));
      runs.set(id, r);
    }
    const s = await stillFor(r.run);
    // a later pick may have finished first
    if (runId !== id) return;
    replay = r;
    shownId = id;
    still = s;
    tick += 1;
  }

  function seek(f: number): void {
    frame = clamp(f);
    if (hasVideo) video.currentTime = (frame + 0.5) / clip.fps;
    else virtualTime = frame / clip.fps;
    tick += 1;
  }

  function play(): void {
    if (hasVideo) {
      video.play().catch(() => {});
      return;
    }
    playing = true;
    lastTs = 0;
    requestAnimationFrame(advance);
  }

  function pause(): void {
    if (hasVideo) video.pause();
    playing = false;
  }

  function toggle(): void {
    if (playing) pause();
    else play();
  }

  function stepBy(dir: -1 | 1): void {
    pause();
    seek(frame - (frame % clip.vid_stride) + dir * clip.vid_stride);
  }

  function setRate(r: number): void {
    rate = r;
    if (hasVideo) video.playbackRate = r;
  }

  function advance(ts: number): void {
    if (!playing || hasVideo) return;
    if (lastTs) virtualTime = (virtualTime + ((ts - lastTs) / 1000) * rate) % (clip.frames / clip.fps);
    lastTs = ts;
    frame = clamp(Math.floor(virtualTime * clip.fps));
    tick += 1;
    requestAnimationFrame(advance);
  }

  function attachVideo(): Promise<boolean> {
    return new Promise((resolve) => {
      video.addEventListener('loadeddata', () => resolve(true), { once: true });
      video.addEventListener('error', () => resolve(false), { once: true });
      video.src = url(clip.media.video);
    });
  }

  function followVideo(): void {
    video.playbackRate = rate;
    video.addEventListener('play', () => (playing = true));
    video.addEventListener('pause', () => (playing = false));
    // currentTime after a seek sits inside the frame, mediaTime is the frame start
    video.addEventListener('seeked', () => {
      frame = clamp(Math.floor(video.currentTime * clip.fps + 0.001));
      tick += 1;
    });
    if ('requestVideoFrameCallback' in video) {
      const onFrame: VideoFrameRequestCallback = (_now, meta) => {
        frame = clamp(Math.round(meta.mediaTime * clip.fps));
        tick += 1;
        video.requestVideoFrameCallback(onFrame);
      };
      video.requestVideoFrameCallback(onFrame);
    } else {
      const loop = () => {
        if (!video.paused) {
          frame = clamp(Math.floor(video.currentTime * clip.fps + 0.001));
          tick += 1;
        }
        requestAnimationFrame(loop);
      };
      requestAnimationFrame(loop);
    }
  }

  $effect(() => {
    if (!layers.gt || gt || gtMissing) return;
    getJson<GtDoc>(`data/visdrone/clip${clip.id}_gt.json`)
      .then((doc) => {
        gt = new Map(doc.frames.map((f) => [f.frame, f.boxes]));
      })
      .catch(() => {
        gtMissing = true;
        layers.gt = false;
      });
  });

  onMount(() => {
    colors = readColors(root);
    (async () => {
      const gtHead = fetch(url(`data/visdrone/clip${clip.id}_gt.json`), { method: 'HEAD' });
      hasVideo = await attachVideo();
      if (hasVideo) followVideo();
      gtMissing = !(await gtHead.then((r) => r.ok).catch(() => false));
      await pick(runId);
      // open on the first frame with boxes: the first processed frames have none until tracks confirm
      seek(replay!.steps.find((s) => s.tracks.length > 0)?.frame ?? 0);
      if (!matchMedia('(prefers-reduced-motion: reduce)').matches) play();
    })().catch((e: unknown) => {
      error = fill(t.loadError, { error: e instanceof Error ? e.message : String(e) });
    });
    return () => pause();
  });
</script>

<div class="console-root" bind:this={root}>
  {#if error}
    <p class="msg">{error}</p>
  {:else if !replay || !colors}
    <p class="msg">{t.loading}</p>
  {:else}
    <div class="console">
      <div class="screen">
        {#if !hasVideo}<p class="msg">{t.noVideo}</p>{/if}
        <Viewport
          {t}
          {clip}
          {replay}
          {step}
          {frame}
          {tick}
          {layers}
          {selected}
          gt={layers.gt ? gt : null}
          video={hasVideo ? video : null}
          {still}
          {colors}
          onselect={(id) => {
            selected = id;
            tick += 1;
          }}
        />
        <Transport {t} {playing} {rate} {step} {totalIndex} onplaytoggle={toggle} onstep={stepBy} onrate={setRate} />
        <Timeline
          {t}
          {clip}
          {replay}
          {step}
          {frame}
          {colors}
          onseek={(f) => {
            pause();
            seek(f);
          }}
        />
      </div>
      <aside class="rail">
        <Picker {t} {runId} onpick={(id) => pick(id).catch((e: unknown) => (error = String(e)))} />
        <StatusCard {t} {lang} {replay} {step} {frame} />
        <LayersCard {t} {step} bind:layers {gtMissing} />
        <TrackCard {t} {clip} {replay} {selected} />
        <EventLog {t} {clip} {replay} {stepIndex} />
      </aside>
      <div class="outcome">
        <Result {t} runId={shownId} run={replay.run} />
      </div>
    </div>
  {/if}
  <video bind:this={video} class="source" muted playsinline loop preload="auto" aria-hidden="true"></video>
</div>

<style>
  /* on a phone the scenario list comes right after the video, the checks after it */
  .console {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 330px;
    grid-template-rows: auto 1fr;
    grid-template-areas:
      'screen rail'
      'outcome rail';
    gap: 14px;
    align-items: start;
  }

  .screen {
    grid-area: screen;
  }

  .rail {
    grid-area: rail;
  }

  .outcome {
    grid-area: outcome;
    min-width: 0;
  }

  /* minmax(0, 1fr): without it the implicit column grows to the min-content of the checks table */
  .screen,
  .rail {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    gap: 10px;
    align-content: start;
    min-width: 0;
  }

  .msg {
    margin: 0;
    color: var(--muted);
    font-size: 13px;
  }

  /* the video only feeds the canvas; it stays in the page so browsers keep decoding it */
  .source {
    position: fixed;
    left: 0;
    bottom: 0;
    width: 2px;
    height: 2px;
    opacity: 0.01;
    pointer-events: none;
  }

  .console-root :global(.card) {
    padding: 12px 14px;
    border: 1px solid var(--line);
    border-radius: var(--radius);
    background: var(--panel);
  }

  .console-root :global(.card h3) {
    margin-bottom: 10px;
    font-family: var(--f-mono);
    font-size: 13px;
    font-weight: 500;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--muted);
  }

  @media (max-width: 980px) {
    .console {
      grid-template-columns: minmax(0, 1fr);
      grid-template-rows: none;
      grid-template-areas:
        'screen'
        'rail'
        'outcome';
    }

    .rail {
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
    }
  }
</style>
