import { defineConfig, devices } from '@playwright/test';

// End-to-end checks on the production build (npm run build first): what a visitor gets.
export default defineConfig({
  testDir: 'e2e',
  testMatch: '**/*.e2e.ts',
  timeout: 60_000,
  workers: 2,
  reporter: 'list',
  use: {
    baseURL: 'http://127.0.0.1:4330',
    ...devices['Desktop Chrome'],
  },
  webServer: {
    // --ignore-lock: a one-off foreground server that Playwright owns and stops, apart from any dev server
    command: 'npx astro preview --port 4330 --host 127.0.0.1 --ignore-lock',
    url: 'http://127.0.0.1:4330/',
    reuseExistingServer: false,
    timeout: 60_000,
  },
});
