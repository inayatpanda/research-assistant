import { motion } from 'framer-motion'

import { pageEnter } from '@/lib/motion'

export function PagePlaceholder({
  title,
  subtitle,
  phase,
}: {
  title: string
  subtitle: string
  phase: string
}) {
  return (
    <motion.div
      variants={pageEnter}
      initial="initial"
      animate="animate"
      exit="exit"
      className="max-w-3xl mx-auto px-8 py-10"
    >
      <div className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
        {phase}
      </div>
      <h1 className="mt-2 text-2xl font-semibold tracking-tight">{title}</h1>
      <p className="mt-2 text-[14px] text-muted-foreground">{subtitle}</p>
      <div className="mt-6 rounded-lg border border-dashed border-border bg-white/40 p-12 text-center text-[13px] text-muted-foreground">
        This module ships in {phase}.
      </div>
    </motion.div>
  )
}
