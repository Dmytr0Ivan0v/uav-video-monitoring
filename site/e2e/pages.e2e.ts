import AxeBuilder from '@axe-core/playwright';
import { expect, test } from '@playwright/test';
import { PAGES } from './data';

for (const path of PAGES) {
  test.describe(path, () => {
    test('opens without console errors', async ({ page }) => {
      const errors: string[] = [];
      page.on('console', (m) => m.type() === 'error' && errors.push(m.text()));
      page.on('pageerror', (e) => errors.push(e.message));
      const r = await page.goto(path);
      expect(r?.status()).toBe(200);
      await expect(page.locator('h1, h2').first()).toBeVisible();
      await page.waitForLoadState('networkidle');
      expect(errors).toEqual([]);
    });

    test('has no horizontal scroll on a 400 px phone', async ({ page }) => {
      await page.setViewportSize({ width: 400, height: 850 });
      await page.goto(path);
      await page.waitForLoadState('networkidle');
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
      expect(overflow).toBeLessThanOrEqual(0);
    });

    test('has no serious accessibility violations', async ({ page }) => {
      await page.goto(path);
      await page.waitForLoadState('networkidle');
      const { violations } = await new AxeBuilder({ page }).analyze();
      const serious = violations
        .filter((v) => v.impact === 'serious' || v.impact === 'critical')
        .map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(' ')).slice(0, 3).join(', ')}`);
      expect(serious).toEqual([]);
    });
  });
}

test('an unknown address gets the 404 page', async ({ page }) => {
  const r = await page.goto('/no-such-page/');
  expect(r?.status()).toBe(404);
  await expect(page.getByRole('heading', { name: 'Page not found' })).toBeVisible();
});

test('the language switch keeps the page', async ({ page }) => {
  await page.goto('/lab/navigation/');
  await page.getByRole('link', { name: 'Українська' }).click();
  await expect(page).toHaveURL(/\/uk\/lab\/navigation\/$/);
  await expect(page.locator('html')).toHaveAttribute('lang', 'uk');
});
