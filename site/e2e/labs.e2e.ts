import { expect, test } from '@playwright/test';
import { hasMedia, publicJson } from './data';

interface Detector {
  references: { image: string }[];
}
interface Navigation {
  runs: Record<
    'base' | 'blur',
    { ate_m: { rmse: number }; rpe: { trans_rmse_m: number; rot_mean_deg: number }[]; status_counts: Record<string, number> }
  >;
}
interface Change {
  taus: number[];
  shown: { id: string; levels: string }[];
  metrics: Record<string, { tau: number; n_found: number; n_changed: number }[]>;
}

test('the browser detector finds the boxes Python found on all reference frames', async ({ page, request }) => {
  const doc = publicJson<Detector>('data/detector.json');
  test.skip(!(await hasMedia(request, `/${doc.references[0]!.image}`)), 'needs the VisDrone frames built by make export');
  test.setTimeout(180_000);
  await page.goto('/lab/detector/');
  await page.getByRole('button', { name: /Load the model/ }).click();
  await expect(page.locator('.status.ok')).toBeVisible({ timeout: 120_000 });
  await page.getByRole('button', { name: 'Run the check' }).click();
  await expect(page.getByText(/5 of 5 frames pass on/)).toBeVisible({ timeout: 120_000 });
});

test('the navigation lab shows the ATE of each run', async ({ page }) => {
  const doc = publicJson<Navigation>('data/navigation.json');
  await page.goto('/lab/navigation/');
  const metrics = page.locator('.metrics');
  for (const run of [doc.runs.base, doc.runs.blur]) {
    await expect(metrics).toContainText(String(run.ate_m.rmse));
    await expect(metrics).toContainText(`${run.rpe[0]!.trans_rmse_m} m`);
    await expect(metrics).toContainText(`${run.rpe[0]!.rot_mean_deg}°`);
  }
  const side = page.locator('.side');
  await expect(side).toContainText(`${doc.runs.base.ate_m.rmse} m`);
  await page.getByRole('button', { name: /Motion blur/ }).click();
  await expect(side).toContainText(`${doc.runs.blur.ate_m.rmse} m`);
  await expect(side).toContainText(`DEGRADED ${doc.runs.blur.status_counts.DEGRADED}`);
});

test('the time slider moves the moment shown', async ({ page }) => {
  await page.goto('/lab/navigation/');
  const time = page.locator('.side dl').first();
  const before = await time.textContent();
  await page.getByRole('slider', { name: 'Time' }).fill('400');
  await expect(time).not.toHaveText(before!);
});

test('play moves through the run', async ({ page }) => {
  await page.goto('/lab/navigation/');
  const slider = page.getByRole('slider', { name: 'Time' });
  await expect(slider).toHaveValue('0');
  await page.getByRole('button', { name: 'Play' }).click();
  await expect(async () => expect(Number(await slider.inputValue())).toBeGreaterThan(10)).toPass({ timeout: 5000 });
});

test('the change threshold changes what the mask finds', async ({ page }) => {
  const doc = publicJson<Change>('data/change.json');
  const pair = doc.shown[0]!;
  const lowest = doc.metrics[pair.id]!.find((m) => m.tau === doc.taus[0])!;
  await page.goto('/lab/change/');
  await page.locator('input[type="range"]').last().fill('0');
  await expect(page.locator('.side')).toContainText(`${lowest.n_found} / ${lowest.n_changed}`);
});
