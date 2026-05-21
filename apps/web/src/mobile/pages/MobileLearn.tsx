/**
 * Phase M1.2 — MobileLearn.
 *
 * Touch-first version of the desktop Learn hub. The page is structured as:
 *
 *   - Sticky page title "Learn".
 *   - <MobileSearchBar> (debounced 250ms before hitting /api/learn/search).
 *   - <ChipRow> with the five categories.
 *   - When the search query has results, render grouped cross-category
 *     hits above the list. Otherwise render the per-category list,
 *     grouped by the same family heuristic the desktop page uses.
 *   - Tap any entry → navigate to `/m/learn/:category/:slug` (a
 *     full-screen reader rendered by <MobileLearnEntryPage>).
 *
 * Offline support: every list query routes through `cacheable()` so a
 * dropped network falls back to IndexedDB. The reactive "Offline" pill
 * surfaces in the header when the active category was served from
 * cache.
 */
import { useQuery } from '@tanstack/react-query'
import { BookOpen, WifiOff } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'

import { Badge } from '@/components/ui/badge'
import { learnApi, type LearnSearchHit } from '@/lib/api'
import { cn } from '@/lib/utils'

import { ChipRow, type ChipRowOption } from '../components/ChipRow'
import { MobileEmpty } from '../components/MobileEmpty'
import { MobileSearchBar } from '../components/MobileSearchBar'
import { cacheable, entryKey, listKey } from '../lib/offlineLearn'

export type LearnCategory =
  | 'stat-tests'
  | 'checklists'
  | 'economics'
  | 'walkthroughs'
  | 'submission'

const CATEGORIES: ChipRowOption<LearnCategory>[] = [
  { value: 'stat-tests', label: 'Stat tests' },
  { value: 'checklists', label: 'Checklists' },
  { value: 'economics', label: 'Economics' },
  { value: 'submission', label: 'Submission' },
  { value: 'walkthroughs', label: 'Walkthroughs' },
]

const SUBMISSION_FAMILY_ORDER = ['planning', 'writing', 'submitting', 'post-decision']

type Summary = {
  slug: string
  title: string
  short_blurb: string
  family?: string
  reporting_standard?: string
  concept_family?: string
  topic_family?: string
  study_type?: string
}

/**
 * Pick the grouping key used by both the desktop list and the mobile
 * list. Keeps category families visible (e.g. "non-parametric") rather
 * than dumping every entry into one bucket.
 */
function groupKeyFor(it: Summary): string {
  if (it.family) return it.family
  if (it.reporting_standard) return 'Reporting guidelines'
  if (it.concept_family) return it.concept_family
  if (it.topic_family) return it.topic_family
  if (it.study_type) return it.study_type
  return 'all'
}

function orderGroups(category: LearnCategory, keys: string[]): string[] {
  const out = [...keys]
  if (category === 'submission') {
    out.sort((a, b) => {
      const ai = SUBMISSION_FAMILY_ORDER.indexOf(a)
      const bi = SUBMISSION_FAMILY_ORDER.indexOf(b)
      if (ai === -1 && bi === -1) return a.localeCompare(b)
      if (ai === -1) return 1
      if (bi === -1) return -1
      return ai - bi
    })
  } else {
    out.sort((a, b) => a.localeCompare(b))
  }
  return out
}

/** Debounce a value by `ms` milliseconds — equivalent to lodash.debounce
 * but free of additional deps. */
function useDebounced<T>(value: T, ms: number): T {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const id = setTimeout(() => setDebounced(value), ms)
    return () => clearTimeout(id)
  }, [value, ms])
  return debounced
}

export default function MobileLearn() {
  const navigate = useNavigate()
  const [params, setParams] = useSearchParams()
  const initialCat = (params.get('cat') as LearnCategory | null) ?? 'stat-tests'
  const [category, setCategory] = useState<LearnCategory>(initialCat)
  const [search, setSearch] = useState('')
  const debouncedSearch = useDebounced(search.trim(), 250)

  useEffect(() => {
    if ((params.get('cat') ?? 'stat-tests') !== category) {
      const next = new URLSearchParams(params)
      next.set('cat', category)
      setParams(next, { replace: true })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [category])

  // List query (offline-aware). The shape of each entry varies per
  // category, but the queryFn unifies them as `Summary[]` — we only
  // need the small subset of fields below to render the list.
  const listQuery = useQuery({
    queryKey: ['mlearn', 'list', category],
    queryFn: async () => {
      return cacheable<Summary[]>(listKey(category), async () => {
        switch (category) {
          case 'stat-tests':
            return (await learnApi.listStatTests()) as Summary[]
          case 'checklists':
            return (await learnApi.listChecklists()) as Summary[]
          case 'economics':
            return (await learnApi.listEconomics()) as Summary[]
          case 'submission':
            return (await learnApi.listSubmission()) as Summary[]
          case 'walkthroughs':
            return (await learnApi.listWalkthroughs()) as Summary[]
        }
      })
    },
    staleTime: 5 * 60 * 1000,
  })

  // Cross-category search.
  const searchQuery = useQuery({
    queryKey: ['mlearn', 'search', debouncedSearch],
    queryFn: () => learnApi.search(debouncedSearch),
    enabled: debouncedSearch.length >= 2,
    staleTime: 30 * 1000,
  })

  const summaries = listQuery.data?.data ?? []
  const offline = listQuery.data?.offline ?? false

  // Group the current category's entries by family for display.
  const grouped = useMemo(() => {
    const buckets: Record<string, Summary[]> = {}
    for (const it of summaries) {
      const key = groupKeyFor(it)
      if (!buckets[key]) buckets[key] = []
      buckets[key].push(it)
    }
    return buckets
  }, [summaries])
  const groupOrder = useMemo(
    () => orderGroups(category, Object.keys(grouped)),
    [category, grouped],
  )

  const showSearch =
    debouncedSearch.length >= 2 &&
    (searchQuery.data?.length ?? 0) > 0

  return (
    <div className="flex min-h-full flex-col bg-background">
      {/* Page title row */}
      <div className="flex items-center justify-between gap-3 px-4 pt-4 pb-2">
        <div>
          <div className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
            Reference & how-to
          </div>
          <h2 className="text-[20px] font-semibold tracking-tight">Learn</h2>
        </div>
        {offline && (
          <Badge
            data-testid="learn-offline-badge"
            variant="secondary"
            className="flex items-center gap-1 text-[10px] uppercase tracking-wide"
          >
            <WifiOff className="h-3 w-3" />
            Offline
          </Badge>
        )}
      </div>

      <div className="sticky top-0 z-10 bg-background/95 backdrop-blur px-4 pb-2 pt-2">
        <MobileSearchBar
          value={search}
          onChange={setSearch}
          placeholder="Search Learn"
          testId="mobile-learn-search"
        />
      </div>

      <ChipRow<LearnCategory>
        options={CATEGORIES}
        value={category}
        onChange={(v) => setCategory(v)}
        testId="mlearn-chip"
        ariaLabel="Learn category"
      />

      <div className="flex-1 space-y-3 px-4 py-3">
        {showSearch && (
          <SearchResults
            hits={searchQuery.data ?? []}
            query={debouncedSearch}
            onPick={(cat, slug) => navigate(`/m/learn/${cat}/${slug}`)}
          />
        )}

        {listQuery.isLoading && (
          <div className="py-12 text-center text-[13px] text-muted-foreground">
            Loading reference content…
          </div>
        )}

        {!listQuery.isLoading && summaries.length === 0 && (
          <MobileEmpty
            icon={BookOpen}
            title="No entries yet"
            subtitle="This category will be populated soon."
            testId="mlearn-empty"
          />
        )}

        {!listQuery.isLoading && summaries.length > 0 && (
          <div
            data-testid="mlearn-list"
            className="rounded-xl border border-border bg-card divide-y divide-border"
          >
            {groupOrder.map((groupKey) => (
              <div key={groupKey}>
                <div className="px-4 pt-3 pb-1 text-[10px] uppercase tracking-wider text-muted-foreground font-medium">
                  {groupKey.replace(/_/g, ' ').replace(/-/g, ' ')}
                </div>
                {grouped[groupKey].map((it) => (
                  <button
                    key={it.slug}
                    data-testid={`mlearn-entry-${it.slug}`}
                    onClick={() => navigate(`/m/learn/${category}/${it.slug}`)}
                    className={cn(
                      'flex w-full min-h-[64px] items-start gap-2 px-4 py-3 text-left',
                      'transition-colors active:bg-muted/60 hover:bg-muted/40',
                    )}
                  >
                    <div className="min-w-0 flex-1">
                      <div className="truncate text-[14px] font-medium leading-snug">
                        {it.title}
                      </div>
                      <div className="mt-0.5 line-clamp-2 text-[12px] text-muted-foreground">
                        {it.short_blurb}
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function SearchResults({
  hits,
  query,
  onPick,
}: {
  hits: LearnSearchHit[]
  query: string
  onPick: (category: string, slug: string) => void
}) {
  const grouped = useMemo(() => {
    const out: Record<string, LearnSearchHit[]> = {}
    for (const h of hits) {
      const cat = h.category === 'stat_tests' ? 'stat-tests' : h.category
      if (!out[cat]) out[cat] = []
      out[cat].push(h)
    }
    return out
  }, [hits])
  const order = ['stat-tests', 'checklists', 'economics', 'submission', 'walkthroughs']
  const keys = Object.keys(grouped).sort((a, b) => {
    const ai = order.indexOf(a)
    const bi = order.indexOf(b)
    if (ai === -1 && bi === -1) return a.localeCompare(b)
    if (ai === -1) return 1
    if (bi === -1) return -1
    return ai - bi
  })
  return (
    <div
      data-testid="mlearn-search-results"
      className="rounded-xl border border-border bg-card"
    >
      <div className="px-4 py-2 text-[10px] uppercase tracking-wider text-muted-foreground font-medium">
        Search "{query}" — {hits.length} hit{hits.length === 1 ? '' : 's'}
      </div>
      <div className="divide-y divide-border">
        {keys.map((cat) => (
          <div key={cat} className="py-1">
            <div className="px-4 pb-1 pt-2 text-[10px] uppercase tracking-wider text-muted-foreground/80 font-medium">
              {cat.replace(/-/g, ' ')}
            </div>
            {grouped[cat].slice(0, 5).map((h) => (
              <button
                key={`${cat}-${h.slug}`}
                data-testid={`mlearn-search-hit-${h.slug}`}
                onClick={() => onPick(cat, h.slug)}
                className="flex w-full flex-col gap-0.5 px-4 py-2 text-left transition-colors hover:bg-muted/40 active:bg-muted/60"
              >
                <span className="text-[13px] font-medium leading-snug">
                  {h.title}
                </span>
                <span className="line-clamp-2 text-[11px] text-muted-foreground">
                  {h.snippet}
                </span>
              </button>
            ))}
          </div>
        ))}
      </div>
    </div>
  )
}

/** Re-export the helper that `entryKey()` uses elsewhere so a single
 * import surface keeps test mocks tidy. */
export { entryKey as _learnEntryKey }
