// @ts-check
import { defineConfig } from 'astro/config';
import react from '@astrojs/react';

// https://astro.build/config
export default defineConfig({
  integrations: [react()],
  output: 'static',
  server: {
    host: '0.0.0.0',
    port: 4321
  }
});
