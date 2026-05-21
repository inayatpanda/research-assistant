/**
 * Phase 5a + 5c — `<LearnTooltip>` component.
 *
 * Renders an inline help link that points at the Learn hub entry for a
 * given concept. The component supports two rendering modes:
 *
 *   1. Default ("wrap" mode): wraps the children in a dotted-underlined
 *      Link with an info icon. Use this when the whole label should be
 *      clickable (e.g. a section header).
 *
 *   2. `iconOnly` mode (Phase 5c): renders the children verbatim and
 *      appends a small Info icon button beside them. Tooltip + link are
 *      attached to the icon, not the children. Use this when wiring
 *      tooltips into surfaces where you don't want to visually disrupt
 *      the existing label (e.g. a select picker, a forest-plot
 *      summary card, a GRADE table cell).
 *
 * When the concept is unknown to `LEARN_CONCEPT_INDEX`, the component
 * still renders its children but suppresses both the icon and the link
 * unless `forceRender` is set — this prevents broken hover states.
 */
import { HelpCircle, Info } from 'lucide-react'

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
  /**
   * Phase 5c — when set, the children are NOT wrapped in a link. Only a
   * small info icon appears beside them as the tooltip trigger. Keep the
   * surrounding label exactly as it was.
   */
  iconOnly?: boolean
}

/**
 * Inline "what is this?" affordance. The visible content can be plain
 * text (`<LearnTooltip>p-value</LearnTooltip>`) or a custom node.
 */
export function LearnTooltip({
  concept,
  children,
  description,
  className,
  forceRender = false,
  iconOnly = false,
}: LearnTooltipProps) {
  const known = isKnownLearnConcept(concept)
  const label = children ?? concept

  if (!known && !forceRender) {
    return <span className={className}>{label}</span>
  }

  const href = getLearnLink(concept)
  const tooltipBody = description ?? `Open Learn entry for ${concept}`

  if (iconOnly) {
    return (
      <span className={cn('inline-flex items-center gap-1', className)}>
        {label}
        <TooltipProvider delayDuration={150}>
          <Tooltip>
            <TooltipTrigger asChild>
              <a
                href={href}
                data-testid="learn-tooltip-trigger"
                data-concept={concept}
                aria-label={`Learn more about ${concept}`}
                className="inline-flex items-center text-muted-foreground hover:text-foreground transition-colors"
              >
                <Info aria-hidden="true" className="h-3 w-3" />
              </a>
            </TooltipTrigger>
            <TooltipContent>{tooltipBody}</TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </span>
    )
  }

  return (
    <TooltipProvider delayDuration={150}>
      <Tooltip>
        <TooltipTrigger asChild>
          <a
            href={href}
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
          </a>
        </TooltipTrigger>
        <TooltipContent>{tooltipBody}</TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )
}
