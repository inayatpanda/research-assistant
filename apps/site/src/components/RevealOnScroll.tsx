import { useRef, type ReactNode } from 'react'
import { motion, useInView, useReducedMotion } from 'framer-motion'

/**
 * Phase v0.3 — viewport reveal wrapper.
 *
 * Wrap any block in `<RevealOnScroll>` and it'll fade-up + scale in
 * the first time it scrolls into view. Subsequent scrolls don't
 * re-trigger (`once: true`) so long pages don't feel jittery.
 *
 * Honours `prefers-reduced-motion`: when the user has reduced motion
 * enabled we render the children straight away with no transform.
 */
interface RevealOnScrollProps {
  children: ReactNode
  /** Optional class on the motion wrapper (e.g. for layout tweaks). */
  className?: string
  /** Delay in seconds before the animation starts. Defaults to 0. */
  delay?: number
  /** Vertical offset, in pixels, before the reveal. Defaults to 28. */
  offset?: number
}

export function RevealOnScroll({
  children,
  className,
  delay = 0,
  offset = 28,
}: RevealOnScrollProps) {
  const ref = useRef<HTMLDivElement>(null)
  const reduceMotion = useReducedMotion()
  // 15% visibility is enough — feels responsive without firing too late.
  const inView = useInView(ref, { once: true, margin: '0px 0px -10% 0px' })

  // If motion is reduced or jsdom (no IntersectionObserver), render flat.
  if (reduceMotion) {
    return (
      <div ref={ref} className={className}>
        {children}
      </div>
    )
  }

  return (
    <motion.div
      ref={ref}
      className={className}
      initial={{ opacity: 0, y: offset, scale: 0.985 }}
      animate={inView ? { opacity: 1, y: 0, scale: 1 } : undefined}
      transition={{
        duration: 0.55,
        delay,
        ease: [0.16, 1, 0.3, 1], // ease-out-expo-ish
      }}
    >
      {children}
    </motion.div>
  )
}
