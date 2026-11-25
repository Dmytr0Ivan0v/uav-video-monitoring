<script lang="ts">
  import type { Dict } from '../../i18n/en';
  import { GROUPS, groupIndex } from '../../lib/console/classes';
  import type { Step } from '../../lib/console/replay';

  interface Props {
    t: Dict['console'];
    step: Step | null;
    layers: { boxes: boolean; trails: boolean; gt: boolean };
    gtMissing: boolean;
  }

  let { t, step, layers = $bindable(), gtMissing }: Props = $props();

  const counts = $derived.by(() => {
    const c = GROUPS.map(() => 0);
    for (const b of step?.tracks ?? []) c[groupIndex(b[1])]! += 1;
    return c;
  });
</script>

<div class="card">
  <h3>{t.layers.title}</h3>
  <div class="layers">
    <label><input type="checkbox" bind:checked={layers.boxes} /> {t.layers.boxes}</label>
    <label><input type="checkbox" bind:checked={layers.trails} /> {t.layers.trails}</label>
    <label class:off={gtMissing}>
      <input type="checkbox" bind:checked={layers.gt} disabled={gtMissing} />
      {gtMissing ? t.layers.gtMissing : t.layers.gt}
    </label>
  </div>
  <div class="legend">
    {#each GROUPS as g, i (g.key)}
      <div><i style:background="var({g.color})"></i>{t.groups[g.key]}<b>{counts[i]}</b></div>
    {/each}
  </div>
</div>

<style>
  .layers {
    display: grid;
    gap: 6px;
  }

  label {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 13.5px;
    cursor: pointer;
  }

  label.off {
    color: var(--faint);
    cursor: default;
  }

  input {
    accent-color: var(--accent);
  }

  .legend {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 4px 10px;
    margin-top: 10px;
    font-size: 13px;
  }

  .legend div {
    display: flex;
    align-items: center;
    gap: 7px;
  }

  .legend i {
    flex: none;
    width: 10px;
    height: 10px;
    border-radius: 2px;
  }

  .legend b {
    margin-left: auto;
    font-family: var(--f-mono);
    font-weight: 500;
    font-variant-numeric: tabular-nums;
  }
</style>
