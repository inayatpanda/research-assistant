/// <reference types="vitest" />
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import path from 'node:path'

/**
 * Phase D2 — Landing site Vite config.
 *
 * Standalone bundle deployed to Cloudflare Pages. Mirrors the apps/web
 * test setup (jsdom + vitest) so the component vitests run in the same
 * environment as the main app's frontend suite.
 */
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { '@': path.resolve(__dirname, './src') },
  },
  server: { host: '127.0.0.1', port: 5174 },
  build: {
    outDir: 'dist',
    sourcemap: false,
  },
  test: {
    environment: 'jsdom',
    globals: false,
    include: ['src/**/*.{test,spec}.{ts,tsx}'],
    setupFiles: ['./src/test-setup.ts'],
  },
})
