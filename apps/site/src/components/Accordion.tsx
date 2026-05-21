import { useState, type ReactNode } from 'react'
import { ChevronDown } from 'lucide-react'

interface AccordionItemProps {
  question: string
  children: ReactNode
  defaultOpen?: boolean
}

/**
 * Phase D2 — Disclosure widget used on the Docs / FAQ and Sync pages.
 *
 * We deliberately use a plain `<button>`-driven controlled component
 * rather than a Radix primitive because the landing site keeps its
 * dependency footprint small (no shadcn here). The state is local and
 * keyboard accessible — Tab focuses the trigger, Space/Enter toggles.
 */
export function AccordionItem({ question, children, defaultOpen = false }: AccordionItemProps) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="border-b border-slate-200 last:border-b-0">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className="flex w-full items-center justify-between gap-4 py-4 text-left text-base font-medium text-ink hover:text-accent focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-accent"
        aria-expanded={open}
      >
        <span>{question}</span>
        <ChevronDown
          aria-hidden
          className={`h-5 w-5 shrink-0 text-ink-soft transition-transform ${open ? 'rotate-180' : ''}`}
        />
      </button>
      {open ? (
        <div className="pb-5 pr-8 text-sm leading-relaxed text-ink-muted">{children}</div>
      ) : null}
    </div>
  )
}

interface AccordionProps {
  children: ReactNode
}

export function Accordion({ children }: AccordionProps) {
  return <div className="divide-y divide-slate-200 rounded-2xl border border-slate-200 bg-white px-6">{children}</div>
}
