import { expect, test } from '@playwright/test';
import { fact } from './data';

// the first-screen budget fixed before the stage 3 measurement: 250 KB until load, the clip after it
const BUDGET_BYTES = 250 * 1024;

test('the first screen stays in its budget and loads the clip after the page', async ({ page }) => {
  await page.goto('/', { waitUntil: 'load' });
  const { bytes, clipStart, loadStart, scripts } = await page.evaluate(() => {
    const nav = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
    const resources = performance.getEntriesByType('resource') as PerformanceResourceTiming[];
    const before = resources.filter((r) => r.startTime < nav.loadEventStart);
    return {
      bytes: nav.transferSize + before.reduce((s, r) => s + r.transferSize, 0),
      clipStart: resources.find((r) => r.name.endsWith('.mp4'))?.startTime ?? Infinity,
      loadStart: nav.loadEventStart,
      scripts: before.filter((r) => r.initiatorType === 'script').map((r) => r.name),
    };
  });
  expect(bytes).toBeLessThanOrEqual(BUDGET_BYTES);
  expect(clipStart).toBeGreaterThanOrEqual(loadStart);
  expect(scripts).toEqual([]);
});

test('the hero quotes the exported facts', async ({ page }) => {
  await page.goto('/');
  const facts = page.locator('.facts');
  await expect(facts).toContainText(`${fact('frozen_detected')} / ${fact('frozen_expected')}`);
  await expect(facts).toContainText(String(fact('ok_in_freeze_nocheck')));
  await expect(facts).toContainText(String(fact('frame_dropped')));
});

test('contacts appear only after a click', async ({ page }) => {
  await page.goto('/');
  expect(await page.content()).not.toContain('gmail');
  await page.locator('#contact button[data-kind="mailto"]').click();
  await expect(page.locator('#contact a[href^="mailto:"]')).toHaveText(/@gmail\.com$/);
});

test('keyboard focus is visible on the first link of the page', async ({ page }) => {
  await page.goto('/');
  await page.keyboard.press('Tab');
  const outline = await page.evaluate(() => getComputedStyle(document.activeElement!).outlineStyle);
  expect(outline).not.toBe('none');
});
