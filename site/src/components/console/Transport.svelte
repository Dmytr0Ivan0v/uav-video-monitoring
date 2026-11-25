<script lang="ts">
  import type { Dict } from '../../i18n/en';
  import type { Step } from '../../lib/console/replay';
  import { fill } from '../../lib/format';

  interface Props {
    t: Dict['console'];
    playing: boolean;
    rate: number;
    step: Step | null;
    totalIndex: number;
    onplaytoggle: () => void;
    onstep: (dir: -1 | 1) => void;
    onrate: (rate: number) => void;
  }

  let { t, playing, rate, step, totalIndex, onplaytoggle, onstep, onrate }: Props = $props();

  const RATES = [0.25, 0.5, 1];
  const frameTime = $derived(
    step?.ms ? fill(t.transport.frameTime, { ms: step.ms[totalIndex]!.toFixed(1) }) : t.transport.noFrameTime,
  );
</script>

<div class="transport">
  <button class="tbtn" aria-label={t.transport.back} onclick={() => onstep(-1)}>
    <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M3 2h2v12H3zM14 2v12L6 8z" /></svg>
  </button>
  <button class="tbtn" aria-label={playing ? t.transport.pause : t.transport.play} onclick={onplaytoggle}>
    <svg viewBox="0 0 16 16" aria-hidden="true">
      {#if playing}<path d="M3 2h4v12H3zM9 2h4v12H9z" />{:else}<path d="M3 2l11 6-11 6z" />{/if}
    </svg>
  </button>
  <button class="tbtn" aria-label={t.transport.forward} onclick={() => onstep(1)}>
    <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M11 2h2v12h-2zM2 2v12l8-6z" /></svg>
  </button>
  <div class="speed" role="group" aria-label={t.transport.speed}>
    {#each RATES as r (r)}
      <button aria-pressed={r === rate} onclick={() => onrate(r)}>{r}×</button>
    {/each}
  </div>
  <div class="tc mono">{frameTime}</div>
</div>

<style>
  .transport {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px;
  }

  .tbtn {
    display: inline-grid;
    place-items: center;
    width: 36px;
    height: 32px;
    border: 1px solid var(--line);
    border-radius: var(--radius);
    background: var(--panel);
    color: var(--fg);
    cursor: pointer;
  }

  .tbtn:hover {
    border-color: var(--faint);
  }

  svg {
    width: 14px;
    height: 14px;
    fill: currentColor;
  }

  .speed {
    display: inline-flex;
    overflow: hidden;
    border: 1px solid var(--line);
    border-radius: var(--radius);
  }

  .speed button {
    padding: 5px 10px;
    border: 0;
    background: var(--panel);
    color: var(--muted);
    font-family: var(--f-mono);
    font-size: 12px;
    cursor: pointer;
  }

  .speed button[aria-pressed='true'] {
    background: var(--panel-2);
    color: var(--fg);
  }

  .tc {
    margin-left: auto;
    font-size: 13px;
    color: var(--muted);
  }
</style>
