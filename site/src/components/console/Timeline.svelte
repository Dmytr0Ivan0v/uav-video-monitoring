<script lang="ts">
  import type { Dict } from '../../i18n/en';
  import type { Colors } from '../../lib/console/colors';
  import type { Replay, Step } from '../../lib/console/replay';
  import type { ClipDoc } from '../../lib/console/types';
  import { fill } from '../../lib/format';

  interface Props {
    t: Dict['console'];
    clip: ClipDoc;
    replay: Replay;
    step: Step | null;
    frame: number;
    colors: Colors;
    onseek: (frame: number) => void;
  }

  let { t, clip, replay, step, frame, colors, onseek }: Props = $props();

  // vertical axis: twice the 60 ms grid line, taller bars are clipped and labelled
  const MAX_MS = 120;
  const HEIGHT = 96;
  let canvas: HTMLCanvasElement;
  let width = $state(0);
  let dragging = false;

  const stage = $derived.by(() => {
    const i = (name: string) => replay.run.stages.indexOf(name);
    return { decode: i('decode'), pre: i('preprocess'), inf: i('inference'), post: i('postprocess'), track: i('track_other'), total: i('total') };
  });

  const stageText = $derived.by(() => {
    if (!step) return '';
    const ms = step.ms;
    if (!ms) return fill(t.timeline.noStages, { frame: step.frame });
    const f = (v: number) => v.toFixed(1);
    const s = stage;
    const text = fill(t.timeline.stages, {
      frame: step.frame,
      decode: f(ms[s.decode]!),
      prepost: f(ms[s.pre]! + ms[s.post]!),
      inference: f(ms[s.inf]!),
      track: f(ms[s.track]!),
    });
    return step === replay.steps[0] ? text + t.timeline.stagesWarmup : text;
  });

  $effect(() => {
    draw();
  });

  function draw(): void {
    const ctx = canvas.getContext('2d');
    if (!ctx || width === 0) return;
    const dpr = Math.min(2, window.devicePixelRatio || 1);
    const w = Math.round(width);
    if (canvas.width !== w * dpr) {
      canvas.width = w * dpr;
      canvas.height = HEIGHT * dpr;
    }
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, HEIGHT);

    const n = clip.frames;
    const top = 4, barH = 64, stripY = 74, stripH = 10;
    const x = (f: number) => (f / (n - 1)) * (w - 2) + 1;
    const bw = Math.max(1, (w / n) * clip.vid_stride - 1);
    const y = (ms: number) => top + barH - (Math.min(ms, MAX_MS) / MAX_MS) * barH;
    ctx.font = '10px "JetBrains Mono", monospace';

    ctx.strokeStyle = colors.line;
    ctx.lineWidth = 1;
    for (const g of [0, MAX_MS / 2, MAX_MS]) {
      ctx.beginPath();
      ctx.moveTo(0, y(g) + 0.5);
      ctx.lineTo(w, y(g) + 0.5);
      ctx.stroke();
    }
    ctx.fillStyle = colors.faint;
    ctx.fillText(`${MAX_MS} ms`, 4, y(MAX_MS) + 10);
    ctx.fillText(String(MAX_MS / 2), 4, y(MAX_MS / 2) - 2);

    const s = stage;
    for (const st of replay.steps) {
      if (!st.ms) continue;
      const ms = st.ms;
      const parts: [number, string][] = [
        [ms[s.decode]!, colors.decode],
        [ms[s.pre]! + ms[s.post]!, colors.prepost],
        [ms[s.inf]!, colors.inference],
        [ms[s.track]!, colors.track],
      ];
      let acc = 0;
      for (const [v, c] of parts) {
        const y0 = y(acc), y1 = y(acc + v);
        if (y0 - y1 > 0) {
          ctx.fillStyle = c;
          ctx.fillRect(x(st.frame) - bw / 2, y1, bw, y0 - y1);
        }
        acc += v;
      }
      if (ms[s.total]! > MAX_MS) {
        ctx.fillStyle = colors.fg;
        ctx.fillText(fill(t.timeline.warmup, { ms: Math.round(ms[s.total]!) }), x(st.frame) + bw, top + 9);
      }
    }

    const budget = clip.contract.frame_budget_ms;
    ctx.setLineDash([4, 3]);
    ctx.strokeStyle = colors.fg;
    ctx.globalAlpha = 0.6;
    ctx.beginPath();
    ctx.moveTo(0, y(budget) + 0.5);
    ctx.lineTo(w, y(budget) + 0.5);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.globalAlpha = 1;

    for (const st of replay.steps) {
      ctx.fillStyle = st.status === 'frame_dropped' ? colors.drop : st.status === 'frozen' ? colors.frozen : colors.ok;
      ctx.globalAlpha = st.status === 'ok' ? 0.35 : 1;
      ctx.fillRect(x(st.frame) - bw / 2, stripY, bw, stripH);
    }
    ctx.globalAlpha = 1;

    const freeze = replay.run.scenario.freeze;
    if (freeze) {
      const a = x(freeze.start_frame + 1), b = x(freeze.end_frame - 1);
      ctx.fillStyle = colors.frozen;
      ctx.fillRect(a, stripY + stripH + 3, b - a, 3);
      const label = t.timeline.cameraFrozen;
      const lx = Math.min(b + 4, w - ctx.measureText(label).width - 2);
      ctx.fillText(label, lx, stripY + stripH + 8);
    }

    ctx.strokeStyle = colors.accent;
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(x(frame), 0);
    ctx.lineTo(x(frame), HEIGHT);
    ctx.stroke();
  }

  function scrub(e: PointerEvent): void {
    const r = canvas.getBoundingClientRect();
    onseek(Math.round(((e.clientX - r.left) / r.width) * (clip.frames - 1)));
  }
</script>

<div class="timeline">
  <div class="plot" bind:clientWidth={width}>
    <canvas
      bind:this={canvas}
      style:height="{HEIGHT}px"
      aria-label={t.timeline.label}
      onpointerdown={(e) => {
        dragging = true;
        canvas.setPointerCapture(e.pointerId);
        scrub(e);
      }}
      onpointermove={(e) => dragging && scrub(e)}
      onpointerup={() => (dragging = false)}
      onpointercancel={() => (dragging = false)}
    ></canvas>
  </div>
  <div class="legend">
    <span><i style:background="var(--s-decode)"></i>{t.timeline.decode}</span>
    <span><i style:background="var(--s-prepost)"></i>{t.timeline.prepost}</span>
    <span><i style:background="var(--s-infer)"></i>{t.timeline.inference}</span>
    <span><i style:background="var(--s-track)"></i>{t.timeline.track}</span>
    <span class="budget">{fill(t.timeline.budget, { ms: clip.contract.frame_budget_ms })}</span>
  </div>
  <div class="stages mono">{stageText}</div>
</div>

<style>
  .timeline {
    padding: 10px 12px 8px;
    border: 1px solid var(--line);
    border-radius: var(--radius);
    background: var(--panel);
  }

  canvas {
    display: block;
    width: 100%;
    cursor: ew-resize;
    touch-action: none;
  }

  .legend {
    display: flex;
    flex-wrap: wrap;
    gap: 4px 14px;
    margin-top: 6px;
    font-size: 12px;
    color: var(--muted);
  }

  .legend i {
    display: inline-block;
    width: 10px;
    height: 10px;
    margin-right: 5px;
    border-radius: 2px;
    vertical-align: -1px;
  }

  .budget {
    margin-left: auto;
  }

  .stages {
    margin-top: 4px;
    font-size: 12px;
    color: var(--muted);
  }
</style>
