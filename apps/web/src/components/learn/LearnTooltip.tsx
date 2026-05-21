/**
 * Phase 5a — `<LearnTooltip>` component.
 *
 * Renders an inline help link that points at the Learn hub entry for a
 * given concept. The component is intentionally minimal: it owns its
 * trigger styling, accepts arbitrary children for the visible label, and
 * defers tooltip plumbing to the existing Radix-based `<Tooltip>` shell.
 *
 * Phase 5c will wire this across the Statistics page, AI-interpretation
 * cards, and the analysis wizard. For Phase 5a we just ship the
 * primitive + its test surface so future PRs can drop it in.
 */
import { HelpCircle } from 'lucide-react'
import { Link } from 'react-router-dom'

import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { getLearnLink, isKnownLearnConcept } from '@/lib/learn/tooltips'
import { cn } from '@/lib/utils'

export interface LearnTooltipProps {
  /** Friendly concept name — e.g. "t-test", "ANOVA", "shapiro-wilk". */
  concept: string
  /** What the user sees. Defaults to the concept verbatim. */
  children?: React.ReactNode
  /** Tooltip body copy; defaults to "Open Learn -> {concept}". */
  description?: string
  /** Extra className for the visible trigger. */
  className?: string
  /** When true, always render even if the concept is unknown. */
  forceRender?: boolean
}

/**
 * Inline "what is this?" affordance. The visible content can be plain
 * text (`<LearnTooltip>p-value</LearnTooltip>`) or a custom node. When
 * the concept is unknown to `LEARN_CONCEPT_INDEX`, the component renders
 * its children with no link unless `forceRender` is set — this avoids
 * shipping broken hover states across the app while the catalogue is
 * still expanding.
 */
export function LearnTooltip({
  concept,
  children,
  description,
  className,
  forceRender = false,
}: LearnTooltipProps) {
  const known = isKnownLearnConcept(concept)
  const label = children ?? concept

  if (!known && !forceRender) {
    return <span className={className}>{label}</span>
  }

  const href = getLearnLink(concept)

  return (
    <TooltipProvider delayDuration={150}>
      <Tooltip>
        <TooltipTrigger asChild>
          <Link
            to={href}
            data-testid="learn-tooltip-trigger"
            data-concept={concept}
            className={cn(
              'inline-flex items-center gap-1 underline decoration-dotted underline-offset-4 hover:decoration-solid text-foreground',
              className,
            )}
          >
            <span>{label}</span>
            <HelpCircle
              aria-hidden="true"
              className="h-3 w-3 text-muted-foreground"
            />
          </Link>
        </TooltipTrigger>
        <TooltipContent>
          {description ?? `Open Learn entry for ${concept}`}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )
}
