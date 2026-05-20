import type { Config } from 'tailwindcss'

export default {
  darkMode: ['class'],
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    container: {
      center: true,
      padding: '2rem',
      screens: { '2xl': '1400px' },
    },
    // Custom breakpoints for ultra-wide displays. Tailwind's defaults stop
    // at `2xl` (1536px). On 27" iMacs and bigger we want to opt into extra
    // grid columns and a wider rail on the manuscript page.
    //   3xl — 1700px: manuscript right-rail goes 2-col
    //   4xl — 1920px: dashboards / library / checklists go 3-col grids
    screens: {
      sm: '640px',
      md: '768px',
      lg: '1024px',
      xl: '1280px',
      '2xl': '1536px',
      '3xl': '1700px',
      '4xl': '1920px',
    },
    extend: {
      colors: {
        border: 'hsl(var(--border))',
        input: 'hsl(var(--input))',
        ring: 'hsl(var(--ring))',
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        sidebar: { DEFAULT: '#0F1117', foreground: '#FAFAFA' },
        workspace: '#FAFAFA',
        accent: { DEFAULT: '#2563EB', hover: '#1D4ED8', tint: '#EFF6FF', foreground: '#FFFFFF' },
        ai: { DEFAULT: '#7C3AED', tint: 'rgba(124,58,237,0.08)', ring: 'rgba(124,58,237,0.35)' },
        highlight: {
          intro: '#EF4444',
          method: '#3B82F6',
          results: '#22C55E',
          discussion: '#EAB308',
        },
        muted: { DEFAULT: 'hsl(var(--muted))', foreground: 'hsl(var(--muted-foreground))' },
        popover: { DEFAULT: 'hsl(var(--popover))', foreground: 'hsl(var(--popover-foreground))' },
        card: { DEFAULT: 'hsl(var(--card))', foreground: 'hsl(var(--card-foreground))' },
        primary: { DEFAULT: 'hsl(var(--primary))', foreground: 'hsl(var(--primary-foreground))' },
        secondary: { DEFAULT: 'hsl(var(--secondary))', foreground: 'hsl(var(--secondary-foreground))' },
        destructive: { DEFAULT: 'hsl(var(--destructive))', foreground: 'hsl(var(--destructive-foreground))' },
      },
      borderRadius: {
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 2px)',
        sm: 'calc(var(--radius) - 4px)',
      },
      fontFamily: {
        sans: ['Inter Variable', 'Inter', 'system-ui', 'sans-serif'],
        serif: ['Source Serif 4', 'Source Serif Pro', 'Georgia', 'serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'monospace'],
      },
      keyframes: {
        shimmer: { '100%': { transform: 'translateX(100%)' } },
      },
      animation: { shimmer: 'shimmer 1.4s linear infinite' },
    },
  },
  plugins: [],
} satisfies Config
