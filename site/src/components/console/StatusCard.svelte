<script lang="ts">
  import type { Dict } from '../../i18n/en';
  import { cameraFrozenAt, type Replay, type Step } from '../../lib/console/replay';

  interface Props {
    t: Dict['console'];
    lang: string;
    replay: Replay;
    step: Step | null;
    frame: number;
  }

  let { t, lang, replay, step, frame }: Props = $props();

  type Tone = 'ok' | 'drop' | 'frozen';

  const system = $derived.by((): [Tone, string] => {
    if (step?.status === 'frame_dropped') return ['drop', t.status.dropped];
    if (step?.status === 'frozen') return ['frozen', t.status.frozen];
    return ['ok', t.status.ok];
  });

  const camera = $derived.by((): [Tone, string] => {
    if (cameraFrozenAt(replay.run, frame)) return ['frozen', t.status.cameraFrozen];
    if (step?.status === 'frame_dropped') return ['drop', t.status.lost];
    return ['ok', t.status.live];
  });

  const n = (v: number) => v.toLocaleString(lang);
</script>

<div class="card">
  <div class="pair">
    <div class="st" data-tone={system[0]}>
      <div class="k">{t.status.system}</div>
      <div class="v">{system[1]}</div>
    </div>
    <div class="st" data-tone={camera[0]}>
      <div class="k">{t.status.camera}</div>
      <div class="v">{camera[1]}</div>
    </div>
  </div>
  <dl class="counters">
    <div><dt>{t.counters.tracks}</dt><dd>{n(step?.tracks.length ?? 0)}</dd></div>
    <div><dt>{t.counters.events}</dt><dd>{n(step?.events ?? 0)}</dd></div>
    <div><dt>{t.counters.dropped}</dt><dd>{n(step?.dropped ?? 0)}</dd></div>
    <div><dt>{t.counters.frozen}</dt><dd>{n(step?.frozen ?? 0)}</dd></div>
    <div class="bad"><dt>{t.counters.falseOk}</dt><dd>{n(step?.falseOk ?? 0)}</dd></div>
  </dl>
</div>

<style>
  .pair {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
  }

  .st {
    padding: 8px 10px;
    border-left: 3px solid var(--tone);
    border-radius: var(--radius);
    background: var(--panel-2);
  }

  .st[data-tone='ok'] {
    --tone: var(--ok);
  }

  .st[data-tone='drop'] {
    --tone: var(--drop);
  }

  .st[data-tone='frozen'] {
    --tone: var(--frozen);
  }

  .k {
    font-family: var(--f-mono);
    font-size: 11px;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--muted);
  }

  .v {
    margin-top: 2px;
    font-family: var(--f-mono);
    font-size: 15px;
    font-weight: 500;
    color: var(--tone);
    overflow-wrap: anywhere;
  }

  .counters {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px 14px;
    margin: 10px 0 0;
  }

  .counters div {
    display: flex;
    justify-content: space-between;
    gap: 8px;
    padding-bottom: 3px;
    border-bottom: 1px dotted var(--line);
    font-size: 13px;
    color: var(--muted);
  }

  dd {
    margin: 0;
    font-family: var(--f-mono);
    font-weight: 500;
    font-variant-numeric: tabular-nums;
    color: var(--fg);
  }

  .bad {
    grid-column: 1 / -1;
  }

  .bad dd {
    color: var(--frozen);
  }
</style>
