/**
 * Phase 13.5 (MP13.5) — Output Viewer.
 *
 * Scrollable document of every analysis on the active dataset. Each card is
 * expandable/collapsible with a pin-to-top and drag-to-reorder affordance,
 * plus delete-with-confirm. Newest first by default. The user's pin and
 * order are kept in component state (localStorage-keyed per dataset).
 *
 * This is the dominant pane on the Statistics page when a dataset is
 * selected. The existing single AnalysisResultCard rendering is retained but
 * wrapped inside a collapsible row — the OutputViewer replaces the
 * "Analyses ({n})" list section.
 */
import {
  DndContext,
  KeyboardSensor,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors,
  type DragEndEvent,
} from '@dnd-kit/core'
import {
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import {
  BarChart3,
  ChevronDown,
  ChevronRight,
  GripVertical,
  Pin,
  PinOff,
} from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'

import { AnalysisResultCard } from './AnalysisResultCard'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { TEST_LABELS, type Analysis, type Dataset } from '@/lib/api'

type ViewerState = {
  pinned: string[] // analysis ids that are pinned to top
  order: string[] // user-chosen full order (overrides newest-first when present)
  expanded: Record<string, boolean>
}

const DEFAULT: ViewerState = { pinned: [], order: [], expanded: {} }

function storageKey(datasetId: string): string {
  return `output-viewer-v1::${datasetId}`
}

function loadState(datasetId: string): ViewerState {
  try {
    if (typeof localStorage === 'undefined') return DEFAULT
    const raw = localStorage.getItem(storageKey(datasetId))
    if (!raw) return DEFAULT
    const parsed = JSON.parse(raw) as Partial<ViewerState>
    return {
      pinned: parsed.pinned ?? [],
      order: parsed.order ?? [],
      expanded: parsed.expanded ?? {},
    }
  } catch {
    return DEFAULT
  }
}

function saveState(datasetId: string, state: ViewerState) {
  try {
    if (typeof localStorage === 'undefined') return
    localStorage.setItem(storageKey(datasetId), JSON.stringify(state))
  } catch {
    /* ignore */
  }
}

export function OutputViewer({
  projectId,
  dataset,
  analyses,
}: {
  projectId: string
  dataset: Dataset
  analyses: Analysis[]
}) {
  const [state, setState] = useState<ViewerState>(() => loadState(dataset.id))

  // Reset when dataset changes.
  useEffect(() => {
    setState(loadState(dataset.id))
  }, [dataset.id])

  useEffect(() => {
    saveState(dataset.id, state)
  }, [dataset.id, state])

  // Sort: pinned first (preserve pin order), then user-chosen order, then
  // newest-first for any analyses without an explicit order.
  const ordered = useMemo(() => {
    const byId = new Map(analyses.map((a) => [a.id, a]))
    const pinned: Analysis[] = []
    for (const id of state.pinned) {
      const a = byId.get(id)
      if (a) {
        pinned.push(a)
        byId.delete(id)
      }
    }
    const ordered: Analysis[] = []
    for (const id of state.order) {
      const a = byId.get(id)
      if (a) {
        ordered.push(a)
        byId.delete(id)
      }
    }
    // Remaining: newest-first (by created_at desc, fall back to original index).
    const rest = Array.from(byId.values()).sort((a, b) =>
      a.created_at < b.created_at ? 1 : a.created_at > b.created_at ? -1 : 0,
    )
    return [...pinned, ...ordered, ...rest]
  }, [analyses, state.pinned, state.order])

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 4 } }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    }),
  )

  const orderedIds = useMemo(() => ordered.map((a) => a.id), [ordered])

  const handleDragEnd = useCallback(
    (e: DragEndEvent) => {
      const { active, over } = e
      if (!over || active.id === over.id) return
      const oldIndex = orderedIds.indexOf(String(active.id))
      const newIndex = orderedIds.indexOf(String(over.id))
      if (oldIndex < 0 || newIndex < 0) return
      const next = [...orderedIds]
      const [moved] = next.splice(oldIndex, 1)
      next.splice(newIndex, 0, moved)
      setState((s) => ({ ...s, order: next }))
    },
    [orderedIds],
  )

  const togglePin = useCallback((id: string) => {
    setState((s) => {
      const isPinned = s.pinned.includes(id)
      return {
        ...s,
        pinned: isPinned
          ? s.pinned.filter((x) => x !== id)
          : [id, ...s.pinned],
      }
    })
  }, [])

  const toggleExpanded = useCallback((id: string) => {
    setState((s) => {
      // Default-expanded means undefined → true. We need an explicit false
      // entry to actually collapse the card; otherwise `!undefined` is true
      // and clicking the chevron doesn't do anything.
      const wasExpanded = s.expanded[id] ?? true
      return {
        ...s,
        expanded: { ...s.expanded, [id]: !wasExpanded },
      }
    })
  }, [])

  if (analyses.length === 0) {
    return (
      <div
        className="rounded-lg border border-dashed border-border bg-white/40 p-8 text-center"
        data-testid="output-viewer-empty"
      >
        <BarChart3 className="h-6 w-6 mx-auto text-muted-foreground" />
        <div className="mt-2 text-[14px] font-medium">No analyses yet</div>
        <div className="mt-1 text-[12px] text-muted-foreground">
          Click <span className="font-medium">New analysis</span> above to run
          your first test on this dataset.
        </div>
      </div>
    )
  }

  return (
    <section className="space-y-3" data-testid="output-viewer">
      <header className="flex items-center justify-between">
        <div className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
          Output viewer ({analyses.length})
        </div>
        <div className="text-[11px] text-muted-foreground">
          Drag to reorder · pin to keep at top
        </div>
      </header>
      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragEnd={handleDragEnd}
      >
        <SortableContext
          items={orderedIds}
          strategy={verticalListSortingStrategy}
        >
          <ul className="space-y-3" data-testid="output-viewer-list">
            {ordered.map((a) => (
              <SortableRow
                key={a.id}
                analysis={a}
                projectId={projectId}
                dataset={dataset}
                pinned={state.pinned.includes(a.id)}
                expanded={state.expanded[a.id] ?? true}
                onTogglePin={() => togglePin(a.id)}
                onToggleExpanded={() => toggleExpanded(a.id)}
              />
            ))}
          </ul>
        </SortableContext>
      </DndContext>
    </section>
  )
}

function SortableRow({
  analysis,
  projectId,
  dataset,
  pinned,
  expanded,
  onTogglePin,
  onToggleExpanded,
}: {
  analysis: Analysis
  projectId: string
  dataset: Dataset
  pinned: boolean
  expanded: boolean
  onTogglePin: () => void
  onToggleExpanded: () => void
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id: analysis.id })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  }

  return (
    <li
      ref={setNodeRef}
      style={style}
      className="rounded-lg border border-border bg-white"
      data-testid={`output-row-${analysis.id}`}
    >
      <div className="flex items-center gap-2 px-3 py-2 border-b border-border">
        <button
          type="button"
          aria-label="Drag to reorder"
          className="text-muted-foreground hover:text-foreground p-1 cursor-grab"
          {...attributes}
          {...listeners}
        >
          <GripVertical className="h-4 w-4" />
        </button>
        <button
          type="button"
          onClick={onToggleExpanded}
          className="text-muted-foreground hover:text-foreground p-1"
          aria-label={expanded ? 'Collapse' : 'Expand'}
          data-testid={`output-toggle-${analysis.id}`}
        >
          {expanded ? (
            <ChevronDown className="h-4 w-4" />
          ) : (
            <ChevronRight className="h-4 w-4" />
          )}
        </button>
        <div className="flex-1 min-w-0">
          <div className="text-[13px] font-medium truncate">
            {/* DEMO-FIX-C — Compose card title from the test label PLUS the
                variable display labels so the user sees
                "Independent t-test · VAS Pain at 6 months × BMI group"
                rather than the canonical snake_case names. */}
            {composeCardTitle(analysis, dataset)}
          </div>
          <div className="text-[11px] text-muted-foreground">
            {new Date(analysis.created_at).toLocaleString()}
          </div>
        </div>
        {pinned && (
          <Badge
            variant="outline"
            className="text-[10px] bg-amber-50 text-amber-700 border-amber-200"
          >
            pinned
          </Badge>
        )}
        <Button
          size="icon"
          variant="ghost"
          className="h-7 w-7"
          onClick={onTogglePin}
          aria-label={pinned ? 'Unpin' : 'Pin to top'}
          data-testid={`output-pin-${analysis.id}`}
        >
          {pinned ? (
            <PinOff className="h-4 w-4 text-muted-foreground" />
          ) : (
            <Pin className="h-4 w-4 text-muted-foreground" />
          )}
        </Button>
      </div>
      {expanded && (
        <div className="p-3">
          <AnalysisResultCard
            projectId={projectId}
            dataset={dataset}
            analysis={analysis}
          />
        </div>
      )}
    </li>
  )
}

/**
 * DEMO-FIX-C — Build a human-readable card title:
 *   "Independent t-test · VAS Pain at 6 months × BMI group"
 *
 * Falls back to just the test label when no variables resolve. Per-chart
 * title overrides (when set) win unconditionally.
 */
function composeCardTitle(analysis: Analysis, dataset: Dataset): string {
  const base = TEST_LABELS[analysis.chosen_test]
  const chart = (analysis.result?.chart ?? null) as Record<string, unknown> | null
  if (chart && typeof chart.title_override === 'string' && chart.title_override.trim()) {
    return `${base} · ${chart.title_override.trim()}`
  }
  const labelOf = (canonical: string): string => {
    const v = dataset.variables.find((x) => x.name === canonical)
    return v?.display_label || v?.name || canonical
  }
  const vars = analysis.variables ?? {}
  const outcome = vars['outcome'] ?? vars['y']
  const groups = vars['groups'] ?? vars['x'] ?? vars['predictor']
  let predictors = vars['predictors']
  if (typeof predictors === 'string') predictors = [predictors]
  const subtitleParts: string[] = []
  if (typeof outcome === 'string') subtitleParts.push(labelOf(outcome))
  if (typeof groups === 'string') subtitleParts.push(labelOf(groups))
  if (Array.isArray(predictors) && predictors.length > 0) {
    const ps = predictors
      .filter((p): p is string => typeof p === 'string')
      .map(labelOf)
    if (ps.length) subtitleParts.push(ps.join(', '))
  }
  if (subtitleParts.length === 0) return base
  return `${base} · ${subtitleParts.join(' × ')}`
}
