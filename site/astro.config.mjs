import { defineConfig } from 'astro/config';
import svelte from '@astrojs/svelte';

export default defineConfig({
  // absolute URLs for canonical, hreflang alternates and Open Graph
  site: 'https://uav.devspace.pp.ua',
  integrations: [svelte()],
  // the browser detector runs multithreaded WASM only on a cross-origin isolated page; nginx sends the same headers
  server: {
    headers: {
      'Cross-Origin-Opener-Policy': 'same-origin',
      'Cross-Origin-Embedder-Policy': 'require-corp',
    },
  },
  vite: {
    // three.js, about 140 KB gzipped, is one chunk loaded only by the navigation lab
    build: { chunkSizeWarningLimit: 600 },
  },
  i18n: {
    locales: ['en', 'uk'],
    defaultLocale: 'en',
  },
});
