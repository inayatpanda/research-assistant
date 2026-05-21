import type { Config } from 'tailwindcss'

/**
 * Phase D2 — Tailwind theme for the landing site.
 *
 * Palette mirrors apps/web (#0F1117 sidebar, #2563EB accent, #FAFAFA
 * workspace) so a visitor who clicks "Download" and opens the app sees
 * the same visual identity. The site adds one extra colour token,
 * "ink", for body copy on the landing page — it's slightly warmer than
 * the app's foreground because long-form marketing text reads better
 * on a softer slate.
 */
export default {
  darkMode: ['class'],
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    container: {
      center: true,
      padding: '1.5rem',
      screens: { '2xl': '1400px' },
    },
    screens: {
      sm: '640px',
      md: '768px',
      lg: '1024px',
      xl: '1280px',
      '2xl': '1536px',
    },
    extend: {
      colors: {
        sidebar: { DEFAULT: '#0F1117', foreground: '#FAFAFA' },
        workspace: '#FAFAFA',
        ink: { DEFAULT: '#1E293B', muted: '#475569', soft: '#64748B' },
        accent: {
          DEFAULT: '#2563EB',
          hover: '#1D4ED8',
          tint: '#EFF6FF',
          foreground: '#FFFFFF',
        },
        highlight: {
          intro: '#EF4444',
          method: '#3B82F6',
          results: '#22C55E',
          discussion: '#EAB308',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        serif: ['Source Serif Pro', 'Georgia', 'serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'monospace'],
      },
      boxShadow: {
        card: '0 1px 2px rgba(15, 17, 23, 0.04), 0 4px 16px rgba(15, 17, 23, 0.06)',
        cta: '0 8px 24px rgba(37, 99, 235, 0.32)',
      },
    },
  },
  plugins: [],
} satisfies Config
