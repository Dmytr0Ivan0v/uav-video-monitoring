<script lang="ts">
  import type { Dict } from '../../i18n/en';
  import { groupIndex } from '../../lib/console/classes';
  import type { Colors } from '../../lib/console/colors';
  import { cameraFrozenAt, type Replay, type Step } from '../../lib/console/replay';
  import type { ClipDoc, GtBox } from '../../lib/console/types';
  import { clock, fill } from '../../lib/format';

  interface Props {
    t: Dict['console'];
    clip: ClipDoc;
    replay: Replay;
    step: Step | null;
    frame: number;
    tick: number;
    layers: { boxes: boolean; trails: boolean; gt: boolean };
    selected: number | null;
    gt: Map<number, GtBox[]> | null;
    video: HTMLVideoElement | null;
    still: HTMLImageElement | null;
    colors: Colors;
    onselect: (id: number | null) => void;
  }

  let { t, clip, replay, step, frame, tick, layers, selected, gt, video, still, colors, onselect }: Props = $props();

  const TRAIL_POINTS = 10;
  let canvas: HTMLCanvasElement;

  const W = $derived(clip.video_size[0]);
  const H = $derived(clip.video_size[1]);
  const k = $derived(W / clip.source_size[0]);
  const pictureFrozen = $derived(cameraFrozenAt(replay.run, frame));
  const falseOk = $derived(step?.status === 'ok' && pictureFrozen);

  $effect(() => {
    void tick;
    draw();
  });

  function draw(): void {
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    const dpr = Math.min(2, window.devicePixelRatio || 1);
    if (canvas.width !== W * dpr) {
      canvas.width = W * dpr;
      canvas.height = H * dpr;
    }
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    if (pictureFrozen && still) ctx.drawImage(still, 0, 0, W, H);
    else if (video && video.readyState >= 2) ctx.drawImage(video, 0, 0, W, H);
    else {
      ctx.fillStyle = '#000';
      ctx.fillRect(0, 0, W, H);
    }
    if (step && step.status !== 'ok') {
      ctx.fillStyle = 'rgba(8, 10, 14, 0.45)';
      ctx.fillRect(0, 0, W, H);
    }

    // boxes and paths are in source pixels
    ctx.save();
    ctx.scale(k, k);
    const px = 1 / k;
    if (layers.gt && gt) {
      const freeze = replay.run.scenario.freeze;
      const shown = pictureFrozen && freeze ? freeze.start_frame : frame;
      ctx.setLineDash([4 * px, 3 * px]);
      ctx.lineWidth = px;
      ctx.strokeStyle = colors.gt;
      for (const [, , x1, y1, x2, y2] of gt.get(shown) ?? []) ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);
      ctx.setLineDash([]);
    }
    const boxes = step?.tracks ?? [];
    const sel = selected != null ? replay.tracks.get(selected) : undefined;
    if (layers.trails && step) {
      ctx.lineWidth = 1.2 * px;
      ctx.globalAlpha = sel ? 0.2 : 0.55;
      for (const [id, cls] of boxes) {
        const pts = replay.tracks.get(id)!.points;
        const end = pts.findIndex((p) => p.frame === step.frame);
        if (end < 1) continue;
        ctx.strokeStyle = colors.groups[groupIndex(cls)]!;
        ctx.beginPath();
        const from = Math.max(0, end - TRAIL_POINTS);
        ctx.moveTo(pts[from]!.x, pts[from]!.y);
        for (let i = from + 1; i <= end; i++) ctx.lineTo(pts[i]!.x, pts[i]!.y);
        ctx.stroke();
      }
      ctx.globalAlpha = 1;
    }
    if (layers.boxes) {
      ctx.lineWidth = 1.4 * px;
      for (const [id, cls, , x1, y1, x2, y2] of boxes) {
        ctx.globalAlpha = sel && id !== selected ? 0.3 : 1;
        ctx.strokeStyle = colors.groups[groupIndex(cls)]!;
        ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);
      }
      ctx.globalAlpha = 1;
    }
    if (sel && step) {
      const upto = sel.points.filter((p) => p.frame <= step.frame);
      if (upto.length > 1) {
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 2 * px;
        ctx.beginPath();
        ctx.moveTo(upto[0]!.x, upto[0]!.y);
        for (const p of upto) ctx.lineTo(p.x, p.y);
        ctx.stroke();
      }
    }
    ctx.restore();

    const box = sel && boxes.find((b) => b[0] === selected);
    if (box) {
      const [id, cls, score, x1, y1, x2, y2] = box;
      const [bx, by, bw, bh] = [x1 * k, y1 * k, (x2 - x1) * k, (y2 - y1) * k];
      ctx.strokeStyle = '#ffffff';
      ctx.lineWidth = 2.5;
      ctx.strokeRect(bx - 2, by - 2, bw + 4, bh + 4);
      const name = t.classes[clip.classes[String(cls)] as keyof typeof t.classes];
      const label = `#${id} ${name} ${score.toFixed(2)}`;
      ctx.font = '500 12px "JetBrains Mono", monospace';
      const lw = ctx.measureText(label).width + 10;
      const lx = Math.min(W - lw, Math.max(0, bx - 2));
      const ly = Math.max(0, by - 22);
      ctx.fillStyle = 'rgba(10, 12, 16, 0.88)';
      ctx.fillRect(lx, ly, lw, 18);
      ctx.fillStyle = '#ffffff';
      ctx.fillText(label, lx + 5, ly + 13);
    }
  }

  function pick(e: MouseEvent): void {
    if (!step) return;
    const r = canvas.getBoundingClientRect();
    const x = ((e.clientX - r.left) / r.width) * clip.source_size[0];
    const y = ((e.clientY - r.top) / r.height) * clip.source_size[1];
    const pad = 4 / k;
    let best: number | null = null;
    let area = Infinity;
    // the smallest box under the pointer wins: small objects sit inside large ones
    for (const [id, , , x1, y1, x2, y2] of step.tracks) {
      if (x >= x1 - pad && x <= x2 + pad && y >= y1 - pad && y <= y2 + pad) {
        const a = (x2 - x1) * (y2 - y1);
        if (a < area) {
          area = a;
          best = id;
        }
      }
    }
    onselect(best);
  }

</script>

<div class="viewport" class:false-ok={falseOk} style:aspect-ratio="{W} / {H}">
  <!-- picking a box is a pointer action; playback has keyboard buttons under the video -->
  <!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_noninteractive_element_interactions -->
  <canvas bind:this={canvas} aria-label={t.viewportLabel} onclick={pick}></canvas>
  <div class="hud tl">
    <span class="rec">●</span>
    {t.hud.camera}
    <span class="extra">
      · {fill(t.hud.source, { w: clip.source_size[0], h: clip.source_size[1], fps: clip.fps, stride: clip.vid_stride })}
    </span>
  </div>
  <div class="hud tr">
    {clock(frame, clip.fps)}<br />{fill(t.hud.frame, { frame, last: clip.frames - 1 })}
  </div>
  {#if step?.status === 'frame_dropped'}
    <div class="banner" style:color="var(--drop)">{t.banner.dropped}<small>{t.banner.droppedNote}</small></div>
  {:else if step?.status === 'frozen'}
    <div class="banner" style:color="var(--frozen)">{t.banner.frozen}<small>{t.banner.frozenNote}</small></div>
  {/if}
  {#if falseOk}
    <div class="truth-tag">{t.banner.falseOk}</div>
  {/if}
</div>

<style>
  .viewport {
    position: relative;
    background: #000;
    border: 1px solid var(--line);
    border-radius: var(--radius);
    overflow: hidden;
    max-width: 100%;
    cursor: crosshair;
  }

  /* an outline paints above the canvas, an inset shadow would sit under it */
  .viewport.false-ok {
    outline: 3px solid var(--frozen);
    outline-offset: -3px;
  }

  canvas {
    display: block;
    width: 100%;
    height: 100%;
  }

  .hud {
    position: absolute;
    top: 10px;
    font-family: var(--f-mono);
    font-size: 12px;
    color: #e8eef3;
    text-shadow: 0 1px 2px rgba(0, 0, 0, 0.9);
    pointer-events: none;
    font-variant-numeric: tabular-nums;
  }

  .hud.tl {
    left: 12px;
  }

  .hud.tr {
    right: 12px;
    text-align: right;
  }

  .rec {
    color: var(--frozen);
  }

  .banner {
    position: absolute;
    left: 50%;
    top: 50%;
    transform: translate(-50%, -50%);
    padding: 10px 18px;
    border: 1px solid currentColor;
    border-radius: var(--radius);
    background: rgba(10, 12, 16, 0.82);
    font-family: var(--f-mono);
    font-size: 14px;
    font-weight: 500;
    letter-spacing: 0.04em;
    text-align: center;
    pointer-events: none;
  }

  .banner small {
    display: block;
    margin-top: 3px;
    font-size: 11.5px;
    font-weight: 400;
    letter-spacing: 0;
    color: #c9d3dc;
  }

  .truth-tag {
    position: absolute;
    left: 12px;
    bottom: 12px;
    padding: 4px 9px;
    border: 1px solid var(--frozen);
    border-radius: 3px;
    background: rgba(10, 12, 16, 0.85);
    color: var(--frozen);
    font-family: var(--f-mono);
    font-size: 12px;
    pointer-events: none;
  }

  @media (max-width: 560px) {
    .extra {
      display: none;
    }

    .banner {
      padding: 7px 10px;
      font-size: 12px;
    }
  }
</style>
