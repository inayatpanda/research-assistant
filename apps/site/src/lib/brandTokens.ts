/**
 * Brand tokens for the marketing site.
 *
 * These mirror the colour palette already used in apps/web (sidebar
 * #0F1117, accent #2563EB, AI purple #7C3AED, highlight swatches) so a
 * visitor who clicks Download and lands in the desktop app sees the
 * exact same visual identity.
 *
 * Reusable gradient strings live here too so a redesign of the home
 * page or a feature page only needs to touch one place to retune the
 * mood. The Tailwind config already exposes these colours as utility
 * classes; this module is for the cases (inline styles, SVG fills,
 * radial-gradient backgrounds) where Tailwind utilities don't reach.
 */

export const brand = {
  // Foundations
  sidebar: '#0F1117',
  workspace: '#FAFAFA',

  // Marks
  accent: '#2563EB',
  accentHover: '#1D4ED8',
  accentTint: '#EFF6FF',
  aiPurple: '#7C3AED',
  aiPurpleTint: 'rgba(124, 58, 237, 0.08)',

  // Highlight swatches (match Reader's colour-coded highlight tools)
  highlightIntro: '#EF4444',
  highlightMethod: '#3B82F6',
  highlightResults: '#22C55E',
  highlightDiscussion: '#EAB308',

  // Text
  ink: '#1E293B',
  inkMuted: '#475569',
  inkSoft: '#64748B',
} as const

/**
 * Gradient strings. Use as `style={{ background: gradient.heroSky }}` or
 * inside a CSS `background` declaration. Each gradient is named after
 * what it evokes rather than what it is so they read well in JSX.
 */
export const gradient = {
  // Light sky-blue to white wash — used behind the hero.
  heroSky:
    'radial-gradient(60% 70% at 50% 0%, rgba(37, 99, 235, 0.16) 0%, rgba(124, 58, 237, 0.08) 35%, rgba(255, 255, 255, 0) 70%)',

  // Blue→purple horizontal sweep — used for section accents and
  // headline text gradients.
  blueToPurple:
    'linear-gradient(90deg, #2563EB 0%, #7C3AED 100%)',

  // Subtle slate vignette — used behind feature cards for depth.
  slateVignette:
    'radial-gradient(120% 80% at 50% 0%, rgba(15, 17, 23, 0.05) 0%, rgba(15, 17, 23, 0) 60%)',

  // Dark inviting CTA background.
  inkCta:
    'linear-gradient(135deg, #0F1117 0%, #1E293B 100%)',
} as const

/**
 * Mini SVG grid pattern, used as a background-image on hero-style
 * sections. Defining it once here keeps it easy to retune the dot
 * density without editing each page.
 */
export const dotPattern =
  "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24'%3E%3Ccircle cx='1.5' cy='1.5' r='1' fill='%23CBD5E1'/%3E%3C/svg%3E\")"
