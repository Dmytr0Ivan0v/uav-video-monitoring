<script lang="ts">
  import type { Dict } from '../../i18n/en';
  import type { Replay } from '../../lib/console/replay';
  import type { ClipDoc } from '../../lib/console/types';
  import { clock, fill } from '../../lib/format';

  interface Props {
    t: Dict['console'];
    clip: ClipDoc;
    replay: Replay;
    stepIndex: number;
  }

  let { t, clip, replay, stepIndex }: Props = $props();

  const SHOWN = 14;

  const lines = $derived.by(() => {
    const out = [];
    for (let i = stepIndex; i >= Math.max(0, stepIndex - SHOWN + 1); i--) {
      const s = replay.steps[i]!;
      let tag = 'OK', tone = 'ok', text = '', stale = false;
      if (s.status === 'frame_dropped') {
        tag = 'DROP';
        tone = 'drop';
        text = fill(t.log.dropped, { frame: s.frame });
      } else if (s.status === 'frozen') {
        tag = 'FROZEN';
        tone = 'frozen';
        text = fill(t.log.frozen, { frame: s.frame });
      } else {
        text = fill(t.log.ok, { frame: s.frame, n: s.tracks.length });
        if (s.newTracks) text += fill(t.log.new, { n: s.newTracks });
        if (s.endedTracks) text += fill(t.log.ended, { n: s.endedTracks });
        stale = s.cameraFrozen;
      }
      out.push({ key: s.frame, time: clock(s.frame, clip.fps), tag, tone, text, stale });
    }
    return out;
  });
</script>

<div class="card">
  <h3>{t.log.title}</h3>
  <ol class="log mono">
    {#each lines as l (l.key)}
      <li>
        <span>{l.time}</span>
        <span class="tag" data-tone={l.tone}>{l.tag}</span>
        <span>{l.text}{#if l.stale}<span class="warn">{t.log.stale}</span>{/if}</span>
      </li>
    {/each}
  </ol>
</div>

<style>
  .log {
    height: 170px;
    margin: 0;
    padding: 0;
    overflow-y: auto;
    list-style: none;
    font-size: 11.5px;
  }

  li {
    display: grid;
    grid-template-columns: 70px 52px minmax(0, 1fr);
    gap: 6px;
    padding: 2px 0;
    border-bottom: 1px solid color-mix(in srgb, var(--line) 50%, transparent);
    color: var(--muted);
  }

  .tag[data-tone='ok'] {
    color: var(--ok);
  }

  .tag[data-tone='drop'] {
    color: var(--drop);
  }

  .tag[data-tone='frozen'],
  .warn {
    color: var(--frozen);
  }
</style>
