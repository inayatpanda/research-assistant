import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { useMemo } from 'react'
import { toast } from 'sonner'

import { ColourTabs, useActiveColour } from '@/components/compile/ColourTabs'
import { CompiledCard } from '@/components/compile/CompiledCard'
import { EmptySectionState } from '@/components/compile/EmptySectionState'
import { SectionDraftPanel } from '@/components/compile/SectionDraftPanel'
import { SortableCardList } from '@/components/compile/SortableCardList'
import { ProjectSelectGate } from '@/components/library/ProjectSelectGate'
import { Skeleton } from '@/components/ui/skeleton'
import {
  type CompiledCard as CardType,
  type HighlightColour,
  compilationApi,
  projectsApi,
} from '@/lib/api'
import { pageEnter } from '@/lib/motion'
import { useActiveProject } from '@/lib/projectContext'
import { sectionLabels } from '@/lib/tokens'

const COLOURS: HighlightColour[] = ['intro', 'method', 'results', 'discussion']

export default function CompilePage() {
  const projectId = useActiveProject((s) => s.projectId)
  const [activeColour, setActiveColour] = useActiveColour()
  const qc = useQueryClient()

  if (!projectId) return <ProjectSelectGate />

  return <CompileInner projectId={projectId} active={activeColour} setActive={setActiveColour} qc={qc} />
}

function CompileInner({
  projectId,
  active,
  setActive,
  qc,
}: {
  projectId: string
  active: HighlightColour
  setActive: (c: HighlightColour) => void
  qc: ReturnType<typeof useQueryClient>
}) {
  const { data: project } = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => projectsApi.get(projectId),
  })

  // Per-colour counts for the tab badges — fire all four in parallel
  const counts = useMemo(() => ({}), [])
  void counts

  const { data: view, isLoading } = useQuery({
    queryKey: ['compilation', projectId, active],
    queryFn: () => compilationApi.view(projectId, active),
  })

  // Fetch all four colour counts to populate the tab badges
  const countQueries = COLOURS.map((c) =>
    useQuery({
      queryKey: ['compilation', projectId, c],
      queryFn: () => compilationApi.view(projectId, c),
    }),
  )
  const tabCounts: Partial<Record<HighlightColour, number>> = {}
  COLOURS.forEach((c, i) => {
    tabCounts[c] = countQueries[i].data?.cards.length ?? 0
  })

  const reorder = useMutation({
    mutationFn: (newOrder: CardType[]) =>
      compilationApi.reorder(
        projectId,
        active,
        newOrder.map((c, i) => ({ highlight_id: c.highlight_id, sort_order: (i + 1) * 10 })),
      ),
    onMutate: async (newOrder) => {
      // Optimistic update
      const key = ['compilation', projectId, active] as const
      await qc.cancelQueries({ queryKey: key })
      const prev = qc.getQueryData(key)
      qc.setQueryData(key, (old: typeof view) =>
        old ? { ...old, cards: newOrder } : old,
      )
      return { prev }
    },
    onError: (e: Error, _newOrder, ctx) => {
      toast.error(e.message)
      if (ctx?.prev) qc.setQueryData(['compilation', projectId, active], ctx.prev)
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: ['compilation', projectId, active] })
    },
  })

  const cards = view?.cards ?? []
  const items = cards.map((c) => ({ ...c, id: c.highlight_id }))

  return (
    <motion.div
      variants={pageEnter}
      initial="initial"
      animate="animate"
      exit="exit"
      className="max-w-5xl mx-auto px-8 py-10 space-y-6"
    >
      <header>
        <div className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
          Compile · {project?.title ?? 'Loading…'}
        </div>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight">{sectionLabels[active]}</h1>
        <p className="mt-1 text-[13px] text-muted-foreground">
          Cards aggregate every highlight of this colour across all articles in this project.
          Drag to reorder. Generate a draft sentence per card, or a whole paragraph from all of them.
        </p>
      </header>

      <ColourTabs active={active} onChange={setActive} counts={tabCounts} />

      <SectionDraftPanel projectId={projectId} colour={active} cardCount={cards.length} />

      {isLoading && (
        <div className="space-y-3">
          {[0, 1].map((i) => (
            <Skeleton key={i} className="h-[200px] rounded-lg" />
          ))}
        </div>
      )}

      {!isLoading && cards.length === 0 && <EmptySectionState colour={active} />}

      {!isLoading && cards.length > 0 && (
        <SortableCardList
          items={items}
          onReorder={(newItems) => reorder.mutate(newItems)}
          renderItem={(item, drag) => (
            <CompiledCard
              card={item}
              projectId={projectId}
              dragHandleProps={{
                attributes: drag.attributes as unknown as Record<string, unknown>,
                listeners: drag.listeners as unknown as Record<string, unknown> | undefined,
              }}
            />
          )}
        />
      )}
    </motion.div>
  )
}
