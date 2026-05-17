import type { Transition, Variants } from 'framer-motion'

const standard: Transition = { duration: 0.2, ease: [0.2, 0.0, 0.0, 1.0] }
const expressive: Transition = { duration: 0.32, ease: [0.16, 1, 0.3, 1] }

export const pageEnter: Variants = {
  initial: { opacity: 0, y: 4 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.24, ease: [0.2, 0, 0, 1] } },
  exit:    { opacity: 0, y: -4, transition: standard },
}

export const cardEnter = (i = 0): Variants => ({
  initial: { opacity: 0, y: 6 },
  animate: { opacity: 1, y: 0, transition: { ...standard, delay: i * 0.03 } },
})

export const modalIn: Variants = {
  initial: { opacity: 0, scale: 0.96 },
  animate: { opacity: 1, scale: 1, transition: expressive },
  exit:    { opacity: 0, scale: 0.96, transition: standard },
}

export const sidebarSlide: Variants = {
  initial: { x: -20, opacity: 0 },
  animate: { x: 0, opacity: 1, transition: { duration: 0.28, ease: [0.16, 1, 0.3, 1] } },
}

export const aiSuggestionEnter: Variants = {
  initial: { opacity: 0, y: 8 },
  animate: { opacity: 1, y: 0, transition: expressive },
}

export const highlightBloom: Variants = {
  initial: { opacity: 0, scale: 1.04 },
  animate: { opacity: 1, scale: 1, transition: expressive },
}
