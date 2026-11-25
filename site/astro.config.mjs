import { defineConfig } from 'astro/config';
import svelte from '@astrojs/svelte';

export default defineConfig({
  integrations: [svelte()],
  i18n: {
    locales: ['en', 'uk'],
    defaultLocale: 'en',
  },
});
