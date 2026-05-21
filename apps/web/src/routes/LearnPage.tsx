/**
 * Phase 5a + 5b — Learn hub.
 *
 * Mounted at `/projects/:projectId/learn` and linked from SettingsPage as
 * a top-level entry-point ("Reference & how-to"). The Settings tab + nav
 * link both target this URL so the user has two discoverable paths in.
 *
 * Layout:
 *   - Top:    Search box + category tabs.
 *   - Left:   Filtered list of entries, grouped by family / topic family.
 *   - Right:  Selected entry detail with rendered Markdown.
 *
 * Categories live (Phase 5c):
 *   - stat-tests   (Phase 5a)
 *   - checklists   (Phase 5b)
 *   - economics    (Phase 5b)
 *   - submission   (Phase 5b)
 *   - walkthroughs (Phase 5c — long-form end-to-end study narratives)
 *
 * URL contract:
 *   ?slug=<slug>         pre-select that entry on mount.
 *   ?cat=<category>      pre-select the category tab.
 */
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { BookOpen, Clock, Search } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'

import { MarkdownView } from '@/components/learn/MarkdownView'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import {
  learnApi,
  type LearnChecklistSummary,
  type LearnEconomicsSummary,
  type LearnStatTestSummary,
  type LearnSubmissionSummary,
  type LearnWalkthroughSummary,
} from '@/lib/api'
import { pageEnter } from '@/lib/motion'
import { cn } from '@/lib/utils'

type CategoryKey =
  | 'stat-tests'
  | 'checklists'
  | 'economics'
  | 'walkthroughs'
  | 'submission'

const CATEGORIES: { key: CategoryKey; label: string }[] = [
  { key: 'stat-tests', label: 'Stat tests' },
  { key: 'checklists', label: 'Checklists' },
  { key: 'economics', label: 'Economics' },
  { key: 'walkthroughs', label: 'Walkthroughs' },
  { key: 'submission', label: 'Submission' },
]

// Ordering for the submission tab's topic-family groups.
const SUBMISSION_FAMILY_ORDER = [
  'planning',
  'writing',
  'submitting',
  'post-decision',
]

export default function LearnPage() {
  const [params, setParams] = useSearchParams()
  const initialCat = (params.get('cat') as CategoryKey | null) ?? 'stat-tests'
  const [activeCat, setActiveCat] = useState<CategoryKey>(initialCat)
  const initialSlug = params.get('slug')
  const [activeSlug, setActiveSlug] = useState<string | null>(initialSlug)
  const [search, setSearch] = useState('')

  // Keep URL ?cat= in sync when the user switches tabs, and reset the
  // selected slug so each category starts fresh.
  useEffect(() => {
    const current = params.get('cat')
    if (current !== activeCat) {
      const next = new URLSearchParams(params)
      next.set('cat', activeCat)
      next.delete('slug')
      setParams(next, { replace: true })
      setActiveSlug(null)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeCat])

  // --- Stat tests (Phase 5a) ---
  const { data: tests, isLoading: testsLoading } = useQuery({
    queryKey: ['learn', 'stat-tests'],
    queryFn: learnApi.listStatTests,
    staleTime: 5 * 60 * 1000,
  })
  const { data: testDetail } = useQuery({
    queryKey: ['learn', 'stat-test', activeSlug],
    queryFn: () => (activeSlug ? learnApi.getStatTest(activeSlug) : null),
    enabled: !!activeSlug && activeCat === 'stat-tests',
    staleTime: 5 * 60 * 1000,
  })

  // --- Checklists (Phase 5b) ---
  const { data: checklists, isLoading: checklistsLoading } = useQuery({
    queryKey: ['learn', 'checklists'],
    queryFn: learnApi.listChecklists,
    staleTime: 5 * 60 * 1000,
    enabled: activeCat === 'checklists',
  })
  const { data: checklistDetail } = useQuery({
    queryKey: ['learn', 'checklist', activeSlug],
    queryFn: () => (activeSlug ? learnApi.getChecklist(activeSlug) : null),
    enabled: !!activeSlug && activeCat === 'checklists',
    staleTime: 5 * 60 * 1000,
  })

  // --- Economics (Phase 5b) ---
  const { data: economics, isLoading: economicsLoading } = useQuery({
    queryKey: ['learn', 'economics'],
    queryFn: learnApi.listEconomics,
    staleTime: 5 * 60 * 1000,
    enabled: activeCat === 'economics',
  })
  const { data: economicsDetail } = useQuery({
    queryKey: ['learn', 'economics', activeSlug],
    queryFn: () => (activeSlug ? learnApi.getEconomics(activeSlug) : null),
    enabled: !!activeSlug && activeCat === 'economics',
    staleTime: 5 * 60 * 1000,
  })

  // --- Submission (Phase 5b) ---
  const { data: submission, isLoading: submissionLoading } = useQuery({
    queryKey: ['learn', 'submission'],
    queryFn: learnApi.listSubmission,
    staleTime: 5 * 60 * 1000,
    enabled: activeCat === 'submission',
  })
  const { data: submissionDetail } = useQuery({
    queryKey: ['learn', 'submission-item', activeSlug],
    queryFn: () => (activeSlug ? learnApi.getSubmission(activeSlug) : null),
    enabled: !!activeSlug && activeCat === 'submission',
    staleTime: 5 * 60 * 1000,
  })

  // --- Walkthroughs (Phase 5c) ---
  const { data: walkthroughs, isLoading: walkthroughsLoading } = useQuery({
    queryKey: ['learn', 'walkthroughs'],
    queryFn: learnApi.listWalkthroughs,
    staleTime: 5 * 60 * 1000,
    enabled: activeCat === 'walkthroughs',
  })
  const { data: walkthroughDetail } = useQuery({
    queryKey: ['learn', 'walkthrough', activeSlug],
    queryFn: () => (activeSlug ? learnApi.getWalkthrough(activeSlug) : null),
    enabled: !!activeSlug && activeCat === 'walkthroughs',
    staleTime: 5 * 60 * 1000,
  })

  // --- Cross-category search (Phase 5c) ---
  // When the user types more than 1 char in the search input we also hit the
  // backend's /api/learn/search endpoint for cross-category hits. We debounce
  // a tiny bit via the query key + staleTime to avoid a request per keystroke
  // turning into a thundering herd.
  const trimmedSearch = search.trim()
  const { data: crossHits } = useQuery({
    queryKey: ['learn', 'search', trimmedSearch.toLowerCase()],
    queryFn: () => learnApi.search(trimmedSearch),
    enabled: trimmedSearch.length >= 2,
    staleTime: 30 * 1000,
  })

  // Source of truth for the active list (used for default-select effect).
  const activeList = useMemo<
    (
      | LearnStatTestSummary
      | LearnChecklistSummary
      | LearnEconomicsSummary
      | LearnSubmissionSummary
      | LearnWalkthroughSummary
    )[]
    | undefined
  >(() => {
    switch (activeCat) {
      case 'stat-tests':
        return tests
      case 'checklists':
        return checklists
      case 'economics':
        return economics
      case 'submission':
        return submission
      case 'walkthroughs':
        return walkthroughs
      default:
        return undefined
    }
  }, [activeCat, tests, checklists, economics, submission, walkthroughs])

  // Default to the first entry on first render of each category.
  useEffect(() => {
    if (!activeSlug && activeList && activeList.length > 0) {
      setActiveSlug(activeList[0].slug)
    }
  }, [activeList, activeSlug])

  const isListLoading =
    (activeCat === 'stat-tests' && testsLoading) ||
    (activeCat === 'checklists' && checklistsLoading) ||
    (activeCat === 'economics' && economicsLoading) ||
    (activeCat === 'submission' && submissionLoading) ||
    (activeCat === 'walkthroughs' && walkthroughsLoading)

  // --- Build the filtered + grouped list ---
  const grouped = useMemo(() => {
    const q = search.trim().toLowerCase()
    const items = activeList ?? []
    const filtered = items.filter((it) => {
      if (!q) return true
      const fields = [it.title, it.slug, it.short_blurb]
      // Add category-specific searchable fields.
      if ('family' in it) fields.push(it.family)
      if ('reporting_standard' in it) fields.push(it.reporting_standard)
      if ('concept_family' in it) fields.push(it.concept_family)
      if ('topic_family' in it) fields.push(it.topic_family)
      return fields.some((f) => f.toLowerCase().includes(q))
    })

    const buckets: Record<string, typeof filtered> = {}
    for (const it of filtered) {
      let key = 'all'
      if ('family' in it) key = it.family
      else if ('reporting_standard' in it) key = 'Reporting guidelines'
      else if ('concept_family' in it) key = it.concept_family
      else if ('topic_family' in it) key = it.topic_family
      else if ('study_type' in it) key = it.study_type
      if (!buckets[key]) buckets[key] = []
      buckets[key].push(it)
    }
    return buckets
  }, [activeList, search])

  // Choose grouping order — stable per-category.
  const orderedGroups = useMemo(() => {
    const keys = Object.keys(grouped)
    if (activeCat === 'submission') {
      keys.sort((a, b) => {
        const ai = SUBMISSION_FAMILY_ORDER.indexOf(a)
        const bi = SUBMISSION_FAMILY_ORDER.indexOf(b)
        if (ai === -1 && bi === -1) return a.localeCompare(b)
        if (ai === -1) return 1
        if (bi === -1) return -1
        return ai - bi
      })
    } else {
      keys.sort((a, b) => a.localeCompare(b))
    }
    return keys
  }, [grouped, activeCat])

  const searchPlaceholder = useMemo(() => {
    switch (activeCat) {
      case 'stat-tests':
        return 'Search stat tests (Enter for all categories)'
      case 'checklists':
        return 'Search reporting checklists (Enter for all)'
      case 'economics':
        return 'Search health economics (Enter for all)'
      case 'submission':
        return 'Search submission topics (Enter for all)'
      case 'walkthroughs':
        return 'Search walkthroughs (Enter for all)'
      default:
        return 'Search'
    }
  }, [activeCat])

  // When the user has typed something, group cross-category hits per
  // category so we can render an "All categories" panel that links into
  // each result regardless of the active tab.
  const groupedCrossHits = useMemo(() => {
    if (!crossHits || trimmedSearch.length < 2) return null
    const out: Record<string, typeof crossHits> = {}
    for (const h of crossHits) {
      const cat = h.category === 'stat_tests' ? 'stat-tests' : h.category
      if (!out[cat]) out[cat] = []
      out[cat].push(h)
    }
    return out
  }, [crossHits, trimmedSearch])

  return (
    <motion.div
      variants={pageEnter}
      initial="initial"
      animate="animate"
      exit="exit"
      data-testid="learn-page-shell"
      className="mx-auto max-w-7xl px-6 py-8 space-y-6"
    >
      <div className="flex items-center gap-3">
        <BookOpen className="h-5 w-5 text-muted-foreground" />
        <div>
          <div className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
            Reference
          </div>
          <h1 className="mt-0.5 text-2xl font-semibold tracking-tight">Learn</h1>
        </div>
      </div>

      {/* Category tabs */}
      <div
        role="tablist"
        data-testid="learn-category-tabs"
        className="flex flex-wrap items-center gap-1 border-b border-border"
      >
        {CATEGORIES.map((c) => {
          const active = c.key === activeCat
          return (
            <button
              key={c.key}
              role="tab"
              aria-selected={active}
              data-testid={`learn-cat-tab-${c.key}`}
              onClick={() => setActiveCat(c.key)}
              className={cn(
                'relative px-4 py-2 text-[13px] font-medium transition-colors',
                active
                  ? 'text-foreground'
                  : 'text-muted-foreground hover:text-foreground',
              )}
            >
              {c.label}
              {active && (
                <motion.span
                  layoutId="learn-cat-underline"
                  className="absolute left-0 right-0 -bottom-px h-[2px] bg-accent"
                />
              )}
            </button>
          )
        })}
      </div>

      {(
        <div className="grid grid-cols-1 md:grid-cols-[280px_1fr] gap-6 min-h-[60vh]">
          {/* Left: search + list */}
          <div className="space-y-3">
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder={searchPlaceholder}
                data-testid="learn-search-input"
                aria-label="Search Learn entries"
                className="pl-8"
              />
            </div>
            <div
              data-testid="learn-entry-list"
              className="rounded-md border border-border bg-card"
            >
              {isListLoading && (
                <div className="p-3 text-[12px] text-muted-foreground">
                  Loading reference content…
                </div>
              )}
              {!isListLoading && orderedGroups.length === 0 && (
                <div
                  data-testid="learn-no-results"
                  className="p-3 text-[12px] text-muted-foreground"
                >
                  No entries match "{search}".
                </div>
              )}
              {orderedGroups.map((groupKey) => (
                <div
                  key={groupKey}
                  className="border-b border-border last:border-b-0"
                >
                  <div className="px-3 pt-3 pb-1 text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
                    {groupKey.replace(/_/g, ' ').replace(/-/g, ' ')}
                  </div>
                  {grouped[groupKey].map((it) => {
                    const active = it.slug === activeSlug
                    const isChecklist = 'reporting_standard' in it
                    return (
                      <button
                        key={it.slug}
                        data-testid={`learn-entry-${it.slug}`}
                        onClick={() => {
                          setActiveSlug(it.slug)
                          const next = new URLSearchParams(params)
                          next.set('slug', it.slug)
                          next.set('cat', activeCat)
                          setParams(next, { replace: true })
                        }}
                        className={cn(
                          'flex w-full flex-col items-start gap-0.5 px-3 py-2 text-left transition-colors',
                          'text-[13px] hover:bg-muted/60',
                          active && 'bg-muted',
                        )}
                      >
                        <span className="font-medium leading-snug flex items-center gap-1.5 flex-wrap">
                          {it.title}
                          {isChecklist && (
                            <Badge
                              variant="secondary"
                              className="text-[10px] font-medium uppercase tracking-wide"
                              data-testid={`learn-badge-${it.slug}`}
                            >
                              {(it as LearnChecklistSummary).reporting_standard}
                            </Badge>
                          )}
                        </span>
                        <span className="text-[11px] text-muted-foreground line-clamp-2">
                          {it.short_blurb}
                        </span>
                      </button>
                    )
                  })}
                </div>
              ))}
            </div>
          </div>

          {/* Right: detail */}
          <div data-testid="learn-detail-pane">
            {groupedCrossHits && Object.keys(groupedCrossHits).length > 0 && (
              <CrossCategoryHits
                hits={groupedCrossHits}
                query={trimmedSearch}
                onJump={(cat, slug) => {
                  setActiveCat(cat as CategoryKey)
                  setActiveSlug(slug)
                  const next = new URLSearchParams(params)
                  next.set('cat', cat)
                  next.set('slug', slug)
                  setParams(next, { replace: true })
                }}
              />
            )}
            {activeCat === 'stat-tests' && (
              <StatTestDetail detail={testDetail} />
            )}
            {activeCat === 'checklists' && (
              <ChecklistDetail detail={checklistDetail} />
            )}
            {activeCat === 'economics' && (
              <EconomicsDetail detail={economicsDetail} />
            )}
            {activeCat === 'submission' && (
              <SubmissionDetail detail={submissionDetail} />
            )}
            {activeCat === 'walkthroughs' && (
              <WalkthroughDetail detail={walkthroughDetail} />
            )}
          </div>
        </div>
      )}
    </motion.div>
  )
}

// ---------------------------------------------------------------------------
// Detail panes (one per category — small enough to inline)
// ---------------------------------------------------------------------------

function EmptyDetail() {
  return (
    <Card>
      <CardContent className="py-8 text-[13px] text-muted-foreground">
        Pick an entry from the list to read it here.
      </CardContent>
    </Card>
  )
}

function StatTestDetail({
  detail,
}: {
  detail:
    | (Awaited<ReturnType<typeof learnApi.getStatTest>> | null)
    | undefined
}) {
  if (!detail) return <EmptyDetail />
  return (
    <Card>
      <CardHeader>
        <div className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
          {detail.family.replace(/_/g, ' ')}
        </div>
        <CardTitle className="text-[18px]">{detail.title}</CardTitle>
        <div className="mt-1 flex flex-wrap gap-1.5">
          <Badge variant="secondary" className="capitalize">
            worked example: {detail.worked_example_domain}
          </Badge>
          {detail.alternatives.slice(0, 3).map((alt) => (
            <Badge key={alt} variant="outline" className="text-[11px]">
              alt: {alt}
            </Badge>
          ))}
        </div>
      </CardHeader>
      <CardContent>
        <div className="rounded-md bg-muted/40 px-3 py-2 mb-4 text-[13px] text-muted-foreground">
          {detail.when_to_use}
        </div>
        <MarkdownView source={detail.body_md} />
      </CardContent>
    </Card>
  )
}

function ChecklistDetail({
  detail,
}: {
  detail:
    | (Awaited<ReturnType<typeof learnApi.getChecklist>> | null)
    | undefined
}) {
  if (!detail) return <EmptyDetail />
  return (
    <Card>
      <CardHeader>
        <div className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
          Reporting checklist
        </div>
        <CardTitle className="text-[18px] flex items-center gap-2 flex-wrap">
          {detail.title}
          <Badge
            variant="secondary"
            className="text-[11px] uppercase tracking-wide"
            data-testid="learn-detail-standard"
          >
            {detail.reporting_standard}
          </Badge>
          <Badge variant="outline" className="text-[11px]">
            v{detail.version}
          </Badge>
        </CardTitle>
        <div className="mt-1 flex flex-wrap gap-1.5">
          <Badge variant="secondary" className="capitalize">
            worked example: {detail.worked_example_domain}
          </Badge>
          {detail.applies_to_study_types.slice(0, 3).map((st) => (
            <Badge key={st} variant="outline" className="text-[11px]">
              {st}
            </Badge>
          ))}
        </div>
        <a
          href={detail.official_url}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-2 text-[11px] text-accent-foreground/80 hover:underline inline-block"
        >
          Official guideline -&gt;
        </a>
      </CardHeader>
      <CardContent>
        <MarkdownView source={detail.body_md} />
      </CardContent>
    </Card>
  )
}

function EconomicsDetail({
  detail,
}: {
  detail:
    | (Awaited<ReturnType<typeof learnApi.getEconomics>> | null)
    | undefined
}) {
  if (!detail) return <EmptyDetail />
  return (
    <Card>
      <CardHeader>
        <div className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
          {detail.concept_family.replace(/-/g, ' ')}
        </div>
        <CardTitle className="text-[18px]">{detail.title}</CardTitle>
        <div className="mt-1 flex flex-wrap gap-1.5">
          <Badge variant="secondary" className="capitalize">
            worked example: {detail.worked_example_domain}
          </Badge>
          {detail.units && (
            <Badge variant="outline" className="text-[11px]">
              units: {detail.units}
            </Badge>
          )}
        </div>
        {detail.formula && (
          <pre className="mt-2 rounded-md bg-muted/40 px-3 py-2 text-[12px] text-muted-foreground overflow-x-auto">
            {detail.formula}
          </pre>
        )}
      </CardHeader>
      <CardContent>
        <MarkdownView source={detail.body_md} />
      </CardContent>
    </Card>
  )
}

function SubmissionDetail({
  detail,
}: {
  detail:
    | (Awaited<ReturnType<typeof learnApi.getSubmission>> | null)
    | undefined
}) {
  if (!detail) return <EmptyDetail />
  return (
    <Card>
      <CardHeader>
        <div className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
          {detail.topic_family.replace(/-/g, ' ')}
        </div>
        <CardTitle className="text-[18px]">{detail.title}</CardTitle>
        <div className="mt-1 flex flex-wrap gap-1.5">
          <Badge variant="secondary" className="capitalize">
            worked example: {detail.worked_example_domain}
          </Badge>
          <Badge variant="outline" className="text-[11px]">
            {detail.topic}
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        <MarkdownView source={detail.body_md} />
      </CardContent>
    </Card>
  )
}

// Extract every H2 from a Markdown body so we can render a sticky TOC.
function extractTocFromMarkdown(src: string): { id: string; text: string }[] {
  const out: { id: string; text: string }[] = []
  for (const raw of src.split('\n')) {
    const line = raw.trim()
    if (line.startsWith('## ') && !line.startsWith('### ')) {
      const text = line.replace(/^##\s+/, '')
      const id = text
        .toLowerCase()
        .replace(/[^a-z0-9\s-]/g, '')
        .replace(/\s+/g, '-')
        .replace(/-+/g, '-')
        .replace(/^-|-$/g, '')
      out.push({ id, text })
    }
  }
  return out
}

function WalkthroughDetail({
  detail,
}: {
  detail:
    | (Awaited<ReturnType<typeof learnApi.getWalkthrough>> | null)
    | undefined
}) {
  if (!detail) return <EmptyDetail />
  const toc = extractTocFromMarkdown(detail.body_md)
  return (
    <div
      data-testid="walkthrough-detail"
      className="grid grid-cols-1 lg:grid-cols-[1fr_220px] gap-6"
    >
      <Card>
        <CardHeader>
          <div className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
            Walkthrough — {detail.study_type.replace(/_/g, ' ')}
          </div>
          <CardTitle className="text-[18px]">{detail.title}</CardTitle>
          <div className="mt-1 flex flex-wrap gap-1.5">
            <Badge
              variant="secondary"
              className="text-[11px] flex items-center gap-1"
              data-testid="walkthrough-reading-time"
            >
              <Clock className="h-3 w-3" />
              {detail.estimated_reading_minutes} min read
            </Badge>
            <Badge variant="secondary" className="capitalize">
              worked example: {detail.worked_example_domain}
            </Badge>
            {detail.related_concepts.slice(0, 4).map((c) => (
              <Badge key={c} variant="outline" className="text-[11px]">
                {c}
              </Badge>
            ))}
          </div>
        </CardHeader>
        <CardContent>
          <MarkdownView source={detail.body_md} />
        </CardContent>
      </Card>
      <aside
        data-testid="walkthrough-toc"
        className="hidden lg:block sticky top-6 self-start"
      >
        <div className="rounded-md border border-border bg-card p-3 text-[12px]">
          <div className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium mb-2">
            On this page
          </div>
          <ol className="space-y-1">
            {toc.map((t) => (
              <li key={t.id}>
                <a
                  href={`#${t.id}`}
                  className="text-muted-foreground hover:text-foreground hover:underline decoration-dotted underline-offset-4"
                >
                  {t.text}
                </a>
              </li>
            ))}
            {toc.length === 0 && (
              <li className="text-muted-foreground">No sections.</li>
            )}
          </ol>
        </div>
      </aside>
    </div>
  )
}

function CrossCategoryHits({
  hits,
  query,
  onJump,
}: {
  hits: Record<string, { category: string; slug: string; title: string; snippet: string }[]>
  query: string
  onJump: (cat: string, slug: string) => void
}) {
  const order = ['stat-tests', 'checklists', 'economics', 'submission', 'walkthroughs']
  const keys = Object.keys(hits).sort((a, b) => {
    const ai = order.indexOf(a)
    const bi = order.indexOf(b)
    if (ai === -1 && bi === -1) return a.localeCompare(b)
    if (ai === -1) return 1
    if (bi === -1) return -1
    return ai - bi
  })
  return (
    <Card data-testid="learn-cross-hits" className="mb-4">
      <CardHeader>
        <CardTitle className="text-[14px]">
          Results across all categories ({Object.values(hits).reduce((a, b) => a + b.length, 0)} for &quot;{query}&quot;)
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {keys.map((cat) => (
          <div key={cat}>
            <div className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium mb-1">
              {cat.replace(/_/g, ' ').replace(/-/g, ' ')} ({hits[cat].length})
            </div>
            <div className="space-y-1">
              {hits[cat].slice(0, 5).map((h) => (
                <button
                  key={`${cat}-${h.slug}`}
                  data-testid={`learn-cross-hit-${h.slug}`}
                  onClick={() => onJump(cat, h.slug)}
                  className="w-full text-left rounded px-2 py-1.5 hover:bg-muted/60 transition-colors"
                >
                  <div className="text-[13px] font-medium">{h.title}</div>
                  <div className="text-[11px] text-muted-foreground line-clamp-2">
                    {h.snippet}
                  </div>
                </button>
              ))}
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  )
}
