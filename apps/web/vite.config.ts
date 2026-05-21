/// <reference types="vitest" />
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import path from 'node:path'
import { VitePWA } from 'vite-plugin-pwa'

/**
 * Phase M0.1 — PWA scaffolding.
 *
 * The PWA serves two audiences:
 *
 *   1. A standalone iPhone/iPad "Add to Home Screen" install that talks
 *      to the user's laptop over a Tailscale tailnet.
 *   2. Any modern desktop browser that pulls the same bundle.
 *
 * We register the service worker with ``autoUpdate`` so a new app
 * version takes effect on the next navigation — important when the
 * laptop pushes a new build but the PWA was left open on a phone.
 *
 * Runtime caching strategies:
 *   - ``/api/*`` GET → NetworkFirst (max 200 entries, 5 minutes). Writes
 *     (POST/PUT/PATCH/DELETE) bypass cache via the explicit ``method``
 *     filter so we never mask a write error with a cached read.
 *   - ``/static/*`` + image assets → CacheFirst (30 days). The
 *     bundler-hashed filenames make eviction trivial.
 */
export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: [
        'favicon.svg',
        'icons/icon-192.png',
        'icons/icon-512.png',
        'icons/apple-touch-icon.png',
      ],
      manifest: {
        name: 'Research Assistant',
        short_name: 'Research',
        description: 'Medical research manuscript assistant',
        theme_color: '#0F1117',
        background_color: '#FAFAFA',
        display: 'standalone',
        start_url: '/',
        icons: [
          {
            src: '/icons/icon-192.png',
            sizes: '192x192',
            type: 'image/png',
          },
          {
            src: '/icons/icon-512.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'any maskable',
          },
        ],
      },
      workbox: {
        // The default precache pattern picks up the built HTML/CSS/JS.
        // We bump the size limit so the larger TipTap + PDF.js chunks
        // can still be precached for offline use.
        globPatterns: ['**/*.{js,css,html,svg,png,ico,webmanifest}'],
        maximumFileSizeToCacheInBytes: 6 * 1024 * 1024,
        // SPA fallback so deep links keep working offline.
        navigateFallback: '/index.html',
        navigateFallbackDenylist: [/^\/api\//, /^\/health$/],
        runtimeCaching: [
          {
            // GET /api/* — short network-first cache. Writes are skipped
            // by the explicit ``method: 'GET'`` filter so the SW never
            // intercepts mutating requests.
            urlPattern: ({ url, request }) =>
              request.method === 'GET' && url.pathname.startsWith('/api/'),
            handler: 'NetworkFirst',
            options: {
              cacheName: 'api-cache',
              networkTimeoutSeconds: 5,
              expiration: {
                maxEntries: 200,
                maxAgeSeconds: 5 * 60,
              },
              cacheableResponse: {
                statuses: [0, 200],
              },
            },
          },
          {
            // Static assets + images.
            urlPattern: ({ url, request }) =>
              request.method === 'GET' &&
              (url.pathname.startsWith('/static/') ||
                /\.(png|jpe?g|gif|webp|svg|ico)$/i.test(url.pathname)),
            handler: 'CacheFirst',
            options: {
              cacheName: 'static-assets',
              expiration: {
                maxEntries: 200,
                maxAgeSeconds: 30 * 24 * 60 * 60,
              },
              cacheableResponse: {
                statuses: [0, 200],
              },
            },
          },
        ],
      },
      // Keep the dev server quiet — the SW only registers on `vite build`.
      devOptions: { enabled: false },
    }),
  ],
  resolve: {
    alias: { '@': path.resolve(__dirname, './src') },
  },
  server: { host: '127.0.0.1', port: 5173 },
  test: {
    environment: 'jsdom',
    globals: false,
    include: ['src/**/*.{test,spec}.{ts,tsx}'],
  },
})
