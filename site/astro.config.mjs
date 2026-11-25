import { defineConfig } from 'astro/config';
import svelte from '@astrojs/svelte';

export default defineConfig({
  integrations: [svelte()],
  // the browser detector runs multithreaded WASM only on a cross-origin isolated page; nginx sends the same headers
  server: {
    headers: {
      'Cross-Origin-Opener-Policy': 'same-origin',
      'Cross-Origin-Embedder-Policy': 'require-corp',
    },
  },
  i18n: {
    locales: ['en', 'uk'],
    defaultLocale: 'en',
  },
});
