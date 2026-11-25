<script lang="ts">
  import type { Dict } from '../../i18n/en';
  import type { Replay } from '../../lib/console/replay';
  import type { ClipDoc } from '../../lib/console/types';
  import { clock, fill } from '../../lib/format';

  interface Props {
    t: Dict['console'];
    clip: ClipDoc;
    replay: Replay;
    selected: number | null;
  }

  let { t, clip, replay, selected }: Props = $props();

  const track = $derived(selected != null ? replay.tracks.get(selected) : undefined);
</script>

<div class="card">
  <h3>{t.track.title}</h3>
  <div class="info">
    {#if track}
      {@const a = track.points[0]!.frame}
      {@const z = track.points[track.points.length - 1]!.frame}
      <b>{fill(t.track.head, { id: track.id, cls: t.classes[clip.classes[String(track.cls)] as keyof typeof t.classes] })}</b><br />
      <span class="mono">{fill(t.track.span, { from: clock(a, clip.fps), to: clock(z, clip.fps), seconds: ((z - a) / clip.fps).toFixed(1) })}</span><br />
      {fill(t.track.stats, { frames: track.points.length, score: (track.scoreSum / track.points.length).toFixed(2) })}
    {:else}
      {t.track.hint}
    {/if}
  </div>
</div>

<style>
  .info {
    font-size: 13px;
    color: var(--muted);
  }

  b {
    font-weight: 600;
    color: var(--fg);
  }
</style>
