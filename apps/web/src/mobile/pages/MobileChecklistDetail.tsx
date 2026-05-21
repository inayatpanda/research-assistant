/**
 * Phase M5.2 — Mobile reporting-checklists detail page.
 *
 * Lives at ``/m/checklists/:type`` (with optional ``?run=<id>``). Renders:
 *   - Back button + checklist title + progress chip "X/N items".
 *   - Scrollable list of checklist items. Each row:
 *       - tap → toggles pass / unclear (mobile-friendly 2-state cycle).
 *       - long-press → opens a BottomSheet with item reference text +
 *         notes textarea + Save.
 *   - Bottom action bar: "Open in desktop" (deep-links the URL-scoped
 *     desktop route).
 *
 * Offline support: per-item toggles are PATCHed to the backend; on a
 * network error we queue the toggle in a local Map and surface a small
 * "Offline — changes queued" banner. The queue auto-flushes when the
 * window regains the ``online`` event.
 *
 * NOTE: the auto-save semantics mean a manually-pressed "Save progress"
 * button would be a placebo — we keep the bottom bar action-light.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Check,
  CheckCircle2,
  Circle,
  Loader2,
  Monitor,
  WifiOff,
} from 'lucide-react'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { toast } from 'sonner'

import { Badge } from '@/components/ui/badge'
import {
  checklistsApi,
  projectsApi,
  type ChecklistItemStatus,
  type ChecklistRunItem,
  type ChecklistRunItemPatch,
  type ChecklistRunRead,
} from '@/lib/api'
import { useLastViewedProject } from '@/lib/projectContext'
import { cn } from '@/lib/utils'

import { BottomSheet } from '../components/BottomSheet'
import { MobileHeader } from '../components/MobileHeader'
import { cacheable, entryKey } from '../lib/offlineLearn'

const LONG_PRESS_MS = 500

export default function MobileChecklistDetail() {
  const navigate = useNavigate()
  const params = useParams<{ type: string }>()
  const checklistKey = params.type ?? ''
  const [search] = useSearchParams()
  const forcedRunId = search.get('run')

  const lastProjectId = useLastViewedProject((s) => s.projectId)
  const qc = useQueryClient()

  const [offlineBanner, setOfflineBanner] = useState(false)
  const queuedRef = useRef<
    Map<string, { itemId: string; patch: ChecklistRunItemPatch }>
  >(new Map())

  const projects = useQuery({
    queryKey: ['projects', 'list'],
    queryFn: () => projectsApi.list(),
    staleTime: 60_000,
  })
  const activeProjectId = useMemo(() => {
    const list = projects.data ?? []
    if (list.length === 0) return null
    const valid = lastProjectId && list.some((p) => p.id === lastProjectId)
    return valid ? lastProjectId : list[0]?.id ?? null
  }, [projects.data, lastProjectId])

  // Look up an existing run for this catalogue + project. If one is in
  // ``?run=<id>``, prefer that. Otherwise pick the most recent matching
  // run, or POST a new one.
  const runsQuery = useQuery({
    queryKey: ['mchecklists', 'runs', activeProjectId],
    queryFn: () => checklistsApi.listRuns(activeProjectId!),
    enabled: !!activeProjectId,
    staleTime: 30_000,
  })
  const catalogueQuery = useQuery({
    queryKey: ['mchecklists', 'catalogue', checklistKey],
    queryFn: () => checklistsApi.getCatalogue(checklistKey),
    enabled: !!checklistKey,
    staleTime: 5 * 60 * 1000,
  })

  const resolvedRunId = useMemo(() => {
    if (forcedRunId) return forcedRunId
    if (!runsQuery.data) return null
    const match = runsQuery.data.find(
      (r) => r.checklist_key === checklistKey,
    )
    return match?.id ?? null
  }, [forcedRunId, runsQuery.data, checklistKey])

  const ensureRun = useMutation({
    mutationFn: async () => {
      if (!activeProjectId) throw new Error('No project selected')
      const cat = catalogueQuery.data
      return checklistsApi.createRun(activeProjectId, {
        checklist_key: checklistKey,
        title: cat?.name ?? checklistKey,
      })
    },
    onSuccess: (run) => {
      // Mirror the {data, offline} shape that ``cacheable()`` produces so
      // the runQuery cache lookup short-circuits.
      qc.setQueryData(['mchecklists', 'run', run.id], {
        data: run,
        offline: false,
      })
      qc.invalidateQueries({
        queryKey: ['mchecklists', 'runs', activeProjectId],
      })
    },
    onError: () => {
      toast.error('Could not create a checklist run')
    },
  })

  // Auto-create a run on first visit if none exists.
  useEffect(() => {
    if (!activeProjectId) return
    if (forcedRunId) return
    if (runsQuery.isLoading) return
    if (resolvedRunId) return
    if (!catalogueQuery.data) return
    if (ensureRun.isPending) return
    ensureRun.mutate()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    activeProjectId,
    forcedRunId,
    runsQuery.isLoading,
    resolvedRunId,
    catalogueQuery.data,
  ])

  const runId = resolvedRunId ?? ensureRun.data?.id ?? null

  const runQuery = useQuery({
    queryKey: ['mchecklists', 'run', runId],
    queryFn: async () => {
      // Offline support via the same cacheable() helper used for Learn.
      return cacheable<ChecklistRunRead>(
        entryKey('checklist-run', runId!),
        async () => checklistsApi.getRun(activeProjectId!, runId!),
      )
    },
    enabled: !!runId && !!activeProjectId,
    staleTime: 10_000,
  })
  const run = runQuery.data?.data
  const fromOfflineCache = runQuery.data?.offline ?? false

  // Patch a single item. Optimistically update the query cache so the
  // tap feels instant; on error, leave the optimistic state in place
  // and queue the patch for re-send when the network comes back.
  const patchItem = useMutation({
    mutationFn: async ({
      itemId,
      patch,
    }: {
      itemId: string
      patch: ChecklistRunItemPatch
    }) => {
      if (!activeProjectId || !runId) throw new Error('Missing run')
      return checklistsApi.patchItem(activeProjectId, runId, itemId, patch)
    },
    onMutate: async ({ itemId, patch }) => {
      const key = ['mchecklists', 'run', runId]
      await qc.cancelQueries({ queryKey: key })
      const prev = qc.getQueryData<{ data: ChecklistRunRead; offline: boolean }>(
        key,
      )
      if (prev?.data) {
        const nextItems = prev.data.items.map((it) =>
          it.item_id === itemId ? { ...it, ...patch } : it,
        )
        qc.setQueryData(key, {
          ...prev,
          data: { ...prev.data, items: nextItems },
        })
      }
      return { prev }
    },
    onSuccess: (fresh) => {
      qc.setQueryData(['mchecklists', 'run', runId], {
        data: fresh,
        offline: false,
      })
    },
    onError: (_err, vars) => {
      // Queue for retry when online events fire.
      queuedRef.current.set(vars.itemId, vars)
      setOfflineBanner(true)
    },
  })

  // Drain the queued patches when the network reports back online.
  const flushQueue = useCallback(async () => {
    if (!activeProjectId || !runId) return
    if (queuedRef.current.size === 0) return
    const queued = Array.from(queuedRef.current.values())
    queuedRef.current.clear()
    for (const q of queued) {
      try {
        await checklistsApi.patchItem(
          activeProjectId,
          runId,
          q.itemId,
          q.patch,
        )
      } catch {
        // Re-queue; we'll try again next online event.
        queuedRef.current.set(q.itemId, q)
      }
    }
    if (queuedRef.current.size === 0) {
      setOfflineBanner(false)
      qc.invalidateQueries({ queryKey: ['mchecklists', 'run', runId] })
    }
  }, [activeProjectId, runId, qc])

  useEffect(() => {
    window.addEventListener('online', flushQueue)
    return () => window.removeEventListener('online', flushQueue)
  }, [flushQueue])

  const counts = useMemo(() => {
    const items = run?.items ?? []
    const done = items.filter(
      (i) => i.status === 'pass' || i.status === 'na',
    ).length
    return { done, total: items.length }
  }, [run])

  // Notes sheet — opened by long-press on an item row.
  const [notesItem, setNotesItem] = useState<ChecklistRunItem | null>(null)
  const [notesDraft, setNotesDraft] = useState('')
  function openNotes(item: ChecklistRunItem) {
    setNotesItem(item)
    setNotesDraft(item.comment ?? '')
  }
  function saveNotes() {
    if (!notesItem) return
    patchItem.mutate({
      itemId: notesItem.item_id,
      patch: { comment: notesDraft },
    })
    setNotesItem(null)
  }

  function cycleStatus(status: ChecklistItemStatus): ChecklistItemStatus {
    // Mobile cycle: pass → unclear → fail → pass. This single-tap UX is
    // intentional — the long-press sheet handles "N/A" + comments.
    if (status === 'pass') return 'unclear'
    if (status === 'unclear') return 'fail'
    return 'pass'
  }

  function onTapItem(item: ChecklistRunItem) {
    patchItem.mutate({
      itemId: item.item_id,
      patch: { status: cycleStatus(item.status) },
    })
  }

  const title = catalogueQuery.data?.name ?? checklistKey

  return (
    <div className="flex min-h-full flex-col bg-background">
      <MobileHeader title={title} onBack={() => navigate(-1)} />

      {/* Progress + offline banner */}
      <div className="flex items-center justify-between gap-2 px-4 pt-3 pb-2">
        <Badge
          variant="secondary"
          className="text-[11px]"
          data-testid="mchecklists-progress"
        >
          {counts.done}/{counts.total} items
        </Badge>
        {(offlineBanner || fromOfflineCache) && (
          <Badge
            data-testid="mchecklists-offline-banner"
            variant="outline"
            className="flex items-center gap-1 text-[10px] uppercase tracking-wide"
          >
            <WifiOff className="h-3 w-3" />
            Offline — changes queued
          </Badge>
        )}
      </div>

      {(runQuery.isLoading || ensureRun.isPending) && (
        <div
          data-testid="mchecklists-loading"
          className="flex items-center justify-center py-12 text-[12px] text-muted-foreground"
        >
          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          Loading checklist…
        </div>
      )}

      {run && (
        <ul
          data-testid="mchecklists-items"
          className="divide-y divide-border border-y border-border bg-card"
        >
          {run.items.map((item) => (
            <ItemRow
              key={item.item_id}
              item={item}
              onTap={() => onTapItem(item)}
              onLongPress={() => openNotes(item)}
            />
          ))}
        </ul>
      )}

      {/* Bottom action bar */}
      <div className="mt-auto sticky bottom-0 z-10 border-t border-border bg-background/95 backdrop-blur px-3 py-2">
        <button
          type="button"
          data-testid="mchecklists-open-desktop"
          onClick={() =>
            activeProjectId &&
            navigate(`/projects/${activeProjectId}/checklists`)
          }
          className="flex w-full items-center justify-center gap-2 rounded-md border border-border bg-card px-3 py-2 text-[13px] font-medium hover:bg-muted"
        >
          <Monitor className="h-4 w-4" />
          Open in desktop
        </button>
      </div>

      {/* Notes sheet */}
      <BottomSheet
        open={!!notesItem}
        onClose={() => setNotesItem(null)}
        title={notesItem ? `Item ${notesItem.item_id}` : 'Notes'}
        snapPoints={['65%']}
      >
        {notesItem && (
          <div className="space-y-3 text-[13px]">
            <div className="rounded-md border border-border bg-muted/40 p-3">
              {notesItem.item_text}
            </div>
            <label className="block">
              <span className="text-[11px] uppercase tracking-wide text-muted-foreground">
                Notes
              </span>
              <textarea
                data-testid="mchecklists-notes-textarea"
                value={notesDraft}
                onChange={(e) => setNotesDraft(e.target.value)}
                rows={5}
                className="mt-1 w-full rounded-md border border-border bg-background p-2 text-[14px] focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/30"
              />
            </label>
            <button
              type="button"
              data-testid="mchecklists-notes-save"
              onClick={saveNotes}
              className="inline-flex h-10 w-full items-center justify-center rounded-md bg-primary px-3 text-[13px] font-semibold text-primary-foreground hover:bg-primary/90"
            >
              Save
            </button>
          </div>
        )}
      </BottomSheet>
    </div>
  )
}

function ItemRow({
  item,
  onTap,
  onLongPress,
}: {
  item: ChecklistRunItem
  onTap: () => void
  onLongPress: () => void
}) {
  const longTimerRef = useRef<number | null>(null)
  const longTriggeredRef = useRef(false)
  const pointerHandledRef = useRef(false)

  function onPointerDown() {
    longTriggeredRef.current = false
    pointerHandledRef.current = false
    longTimerRef.current = window.setTimeout(() => {
      longTriggeredRef.current = true
      onLongPress()
    }, LONG_PRESS_MS)
  }
  function onPointerUp() {
    if (longTimerRef.current != null) {
      window.clearTimeout(longTimerRef.current)
      longTimerRef.current = null
    }
    pointerHandledRef.current = true
    if (!longTriggeredRef.current) onTap()
  }
  function onPointerCancel() {
    if (longTimerRef.current != null) {
      window.clearTimeout(longTimerRef.current)
      longTimerRef.current = null
    }
    longTriggeredRef.current = false
  }

  // ARIA: the checkbox semantics rely on aria-checked. A tap toggles
  // the status; long-press opens notes.
  const isDone = item.status === 'pass' || item.status === 'na'

  return (
    <li className="px-3 py-2">
      <button
        type="button"
        data-testid={`mchecklists-item-${item.item_id}`}
        aria-checked={isDone}
        role="checkbox"
        onPointerDown={onPointerDown}
        onPointerUp={onPointerUp}
        onPointerLeave={onPointerCancel}
        onPointerCancel={onPointerCancel}
        // Click is a fallback for environments without full PointerEvent
        // support (jsdom in vitest). We only fire onTap if the pointer
        // sequence didn't already handle it, and never after a
        // long-press.
        onClick={() => {
          if (pointerHandledRef.current) {
            pointerHandledRef.current = false
            return
          }
          if (longTriggeredRef.current) {
            longTriggeredRef.current = false
            return
          }
          onTap()
        }}
        className={cn(
          'flex w-full items-start gap-3 rounded-md px-2 py-2 text-left transition-colors active:bg-muted/60 hover:bg-muted/40',
        )}
      >
        <span
          className={cn(
            'mt-0.5 inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-full border',
            isDone
              ? 'border-emerald-500 bg-emerald-500 text-white'
              : item.status === 'fail'
                ? 'border-rose-500 bg-rose-50 text-rose-700'
                : item.status === 'unclear'
                  ? 'border-amber-500 bg-amber-50 text-amber-700'
                  : 'border-border bg-card text-muted-foreground',
          )}
          data-testid={`mchecklists-item-status-${item.item_id}`}
          data-status={item.status}
        >
          {isDone ? (
            <Check className="h-3 w-3" />
          ) : item.status === 'unclear' ? (
            <CheckCircle2 className="h-3 w-3" />
          ) : (
            <Circle className="h-3 w-3" />
          )}
        </span>
        <div className="min-w-0 flex-1">
          <div className="text-[13px] font-medium leading-tight">
            {item.item_id}
          </div>
          <div className="mt-0.5 text-[12px] text-muted-foreground leading-snug">
            {item.item_text}
          </div>
          {item.comment && (
            <div
              data-testid={`mchecklists-item-comment-${item.item_id}`}
              className="mt-1 text-[11px] italic text-muted-foreground"
            >
              {item.comment}
            </div>
          )}
        </div>
      </button>
    </li>
  )
}
