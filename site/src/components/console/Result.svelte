<script lang="ts">
  import type { Dict } from '../../i18n/en';
  import { deltaText, limits, storyVars, valueText } from '../../lib/console/checks';
  import type { RunId } from '../../lib/console/runs';
  import type { CheckRow, RunDoc } from '../../lib/console/types';
  import { fill } from '../../lib/format';

  interface Props {
    t: Dict['console'];
    runId: RunId;
    run: RunDoc;
  }

  let { t, runId, run }: Props = $props();

  const story = $derived.by(() => {
    const vars = storyVars(run);
    return t.stories[runId].map((p) => fill(p, vars));
  });
  const verdict = $derived(limits(run.checks));
  const hardware = $derived(run.engine.gpu ? `${run.engine.gpu} · ${run.engine.cpu}` : run.engine.cpu);

  function checkName(row: CheckRow): string {
    const name = t.checks[row.check as keyof typeof t.checks];
    if (row.check === 'switches_window') {
      const [from, to] = (row.detail?.mot_frames as [number, number] | undefined) ?? [0, 0];
      return fill(name, { from, to });
    }
    return name;
  }

  function limit(row: CheckRow): string {
    if (row.threshold == null) return '-';
    if (typeof row.threshold === 'number') return fill(t.table.maxDrop, { v: row.threshold.toFixed(2) });
    return t.thresholds[row.threshold as keyof typeof t.thresholds];
  }

  function framesText(row: CheckRow): string {
    return row.frames === 'all' ? t.table.all : row.frames === 'common' ? t.table.common : '-';
  }
</script>

<div class="result">
  <div class="card text">
    <h3>
      {t.result.title}<span class="verdict" class:fail={verdict.passed < verdict.total}>{fill(t.result.limits, verdict)}</span>
    </h3>
    <h2>{t.runs[runId].title}</h2>
    {#each story as p (p)}
      <p>{p}</p>
    {/each}
  </div>
  <div class="card">
    <div class="tbl">
      <table>
        <thead>
          <tr>
            <th>{t.table.check}</th>
            <th>{t.table.frames}</th>
            <th>{t.table.reference}</th>
            <th>{t.table.value}</th>
            <th>{t.table.delta}</th>
            <th>{t.table.limit}</th>
            <th>{t.table.result}</th>
          </tr>
        </thead>
        <tbody>
          {#each run.checks as row (row.check)}
            <tr>
              <td>{checkName(row)}</td>
              <td>{framesText(row)}</td>
              <td class="n">{valueText(row, 'm0')}</td>
              <td class="n">{valueText(row, 'ms')}</td>
              <td class="n">{deltaText(row)}</td>
              <td>{limit(row)}</td>
              <td class="n">
                {#if row.result === 'pass'}<span class="p">{t.table.pass}</span>
                {:else if row.result === 'fail'}<span class="f">{t.table.fail}</span>
                {:else}-{/if}
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
    <p class="note">{t.result.protocol}</p>
    <p class="src mono">{fill(t.result.source, { run: run.run })}<br />{fill(t.result.hardware, { hardware })}</p>
  </div>
</div>

<style>
  .result {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    gap: 10px;
  }

  h2 {
    margin-bottom: 8px;
    font-size: 22px;
  }

  .text p {
    margin: 0;
    color: var(--muted);
  }

  .text p + p {
    margin-top: 8px;
  }

  .verdict {
    margin-left: 8px;
    padding: 2px 8px;
    border: 1px solid currentColor;
    border-radius: 3px;
    font-size: 12px;
    color: var(--ok);
    vertical-align: 2px;
  }

  .verdict.fail {
    color: var(--frozen);
  }

  .tbl {
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
    letter-spacing: 0.05em;
    color: var(--muted);
  }

  td.n {
    font-family: var(--f-mono);
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
  }

  .p {
    color: var(--ok);
  }

  .f {
    color: var(--frozen);
  }

  .note {
    margin: 8px 0 0;
    font-size: 12px;
    color: var(--muted);
  }

  .src {
    margin: 6px 0 0;
    font-size: 12px;
    color: var(--faint);
    overflow-wrap: anywhere;
  }

</style>
