<script lang="ts">
  import type { Dict } from '../../i18n/en';
  import { ENGINES, STREAMS, type RunId } from '../../lib/console/runs';

  interface Props {
    t: Dict['console'];
    runId: RunId;
    onpick: (id: RunId) => void;
  }

  let { t, runId, onpick }: Props = $props();

  const groups = $derived([
    { title: t.picker.streams, ids: STREAMS },
    { title: t.picker.engines, ids: ENGINES },
  ]);
</script>

<div class="card">
  <h3>{t.picker.title}</h3>
  {#each groups as g (g.title)}
    <fieldset>
      <legend>{g.title}</legend>
      {#each g.ids as id (id)}
        <label>
          <input type="radio" name="console-run" value={id} checked={id === runId} onchange={() => onpick(id)} />
          <span>
            <b>{t.runs[id].title}</b>
            <small>{t.runs[id].note}</small>
          </span>
        </label>
      {/each}
    </fieldset>
  {/each}
</div>

<style>
  fieldset {
    display: grid;
    gap: 6px;
    margin: 0;
    padding: 0;
    border: 0;
  }

  fieldset + fieldset {
    margin-top: 12px;
  }

  legend {
    margin-bottom: 6px;
    padding: 0;
    font-size: 12px;
    color: var(--muted);
  }

  label {
    display: grid;
    grid-template-columns: 16px minmax(0, 1fr);
    gap: 9px;
    padding: 7px 10px;
    border: 1px solid var(--line);
    border-radius: var(--radius);
    background: var(--panel-2);
    cursor: pointer;
  }

  label:has(input:checked) {
    border-color: var(--accent);
  }

  input {
    margin: 3px 0 0;
    accent-color: var(--accent);
  }

  b {
    display: block;
    font-size: 14px;
    font-weight: 600;
  }

  small {
    display: block;
    font-size: 12.5px;
    line-height: 1.4;
    color: var(--muted);
  }
</style>
