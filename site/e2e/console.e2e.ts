import { expect, test, type Page } from '@playwright/test';
import { en } from '../src/i18n/en';
import { fact, publicJson } from './data';

const clip = publicJson<{ frames: number }>('data/console/clip137.json');

// with reduced motion the console does not start playing by itself, so a seek stays where it was put
test.use({ reducedMotion: 'reduce' });

async function openConsole(page: Page): Promise<void> {
  await page.goto('/#console');
  await expect(page.locator('.console')).toBeVisible();
}

// the replay loads after the click: wait for the result of that run before seeking
async function pick(page: Page, run: keyof typeof en.console.runs): Promise<void> {
  await page.locator(`input[value="${run}"]`).check();
  await expect(page.locator('.result h2')).toHaveText(en.console.runs[run].title);
}

// a click on the timeline at the frame; locator.click scrolls the timeline into view first
async function seek(page: Page, frame: number): Promise<void> {
  const canvas = page.locator('.timeline canvas');
  const box = (await canvas.boundingBox())!;
  await canvas.click({ position: { x: 1 + (frame / (clip.frames - 1)) * (box.width - 2), y: 20 } });
  await expect(page.locator('.hud.tr')).toContainText(`frame ${frame} /`);
}

test('without the frozen check the system reports ok on a frozen picture', async ({ page }) => {
  await openConsole(page);
  await pick(page, 'freeze_nocheck');
  await seek(page, 114);
  await expect(page.locator('.truth-tag')).toBeVisible();
  await expect(page.locator('.st').first()).toContainText('OK');
  await expect(page.locator('.st').nth(1)).toContainText('FROZEN');
});

test('the false ok counter ends at the number of the scenario table', async ({ page }) => {
  await openConsole(page);
  await pick(page, 'freeze_nocheck');
  await seek(page, clip.frames - 1);
  await expect(page.locator('.counters .bad dd')).toHaveText(fact('ok_in_freeze_nocheck').toLocaleString('en'));
});

test('with the check the frozen frames are flagged and no box is reported', async ({ page }) => {
  await openConsole(page);
  await pick(page, 'freeze');
  await seek(page, 114);
  await expect(page.locator('.banner')).toContainText('CAMERA FROZEN');
  await seek(page, clip.frames - 1);
  await expect(page.locator('.counters .bad dd')).toHaveText(String(fact('ok_in_freeze_check')));
});

test('a dropped frame shows its banner', async ({ page }) => {
  await openConsole(page);
  await pick(page, 'drop_every');
  // frame_dropped events sit on every fifth processed frame: the first one is frame 8
  const run = publicJson<{ dropped: { frame: number }[] }>('data/console/drop_every.json');
  await seek(page, run.dropped[0]!.frame);
  await expect(page.locator('.banner')).toContainText('FRAME DROPPED');
});

test('playback works from the keyboard', async ({ page }) => {
  await openConsole(page);
  const play = page.getByRole('button', { name: 'Play' });
  await play.focus();
  await page.keyboard.press('Enter');
  await expect(page.getByRole('button', { name: 'Pause' })).toBeVisible();
});
