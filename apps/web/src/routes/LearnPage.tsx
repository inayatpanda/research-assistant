/**
 * Phase 5a — Learn hub.
 *
 * Mounted at `/projects/:projectId/learn` and linked from SettingsPage as
 * a top-level entry-point ("Reference & how-to"). The Settings tab + nav
 * link both target this URL so the user has two discoverable paths in.
 *
 * Layout:
 *   - Top:    Search box + category tabs (Stat tests is the only live tab;
 *             the rest render a "Coming soon" placeholder.)
 *   - Left:   Filtered list of entries, grouped by family.
 *   - Right:  Selected entry detail with rendered Markdown.
 *
 * URL contract:
 *   ?slug=<stat-test-slug>  → pre-select that entry on mount.
 *   ?cat=<category>         → pre-select the category tab.
 */
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { BookOpen, Search } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'

import { MarkdownView } from '@/components/learn/MarkdownView'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { learnApi } from '@/lib/api'
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

export default function LearnPage() {
  const [params, setParams] = useSearchParams()
  const initialCat = (params.get('cat') as CategoryKey | null) ?? 'stat-tests'
  const [activeCat, setActiveCat] = useState<CategoryKey>(initialCat)
  const initialSlug = params.get('slug')
  const [activeSlug, setActiveSlug] = useState<string | null>(initialSlug)
  const [search, setSearch] = useState('')

  // Keep URL ?cat= in sync when the user switches tabs.
  useEffect(() => {
    const current = params.get('cat')
    if (current !== activeCat) {
      const next = new URLSearchParams(params)
      next.set('cat', activeCat)
      setParams(next, { replace: true })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeCat])

  const { data: tests, isLoading } = useQuery({
    queryKey: ['learn', 'stat-tests'],
    queryFn: learnApi.listStatTests,
    staleTime: 5 * 60 * 1000,
  })

  const { data: detail } = useQuery({
    queryKey: ['learn', 'stat-test', activeSlug],
    queryFn: () => (activeSlug ? learnApi.getStatTest(activeSlug) : null),
    enabled: !!activeSlug && activeCat === 'stat-tests',
    staleTime: 5 * 60 * 1000,
  })

  // Build the filtered + grouped list.
  const grouped = useMemo(() => {
    const q = search.trim().toLowerCase()
    const filtered = (tests ?? []).filter((t) => {
      if (!q) return true
      return (
        t.title.toLowerCase().includes(q) ||
        t.slug.toLowerCase().includes(q) ||
        t.short_blurb.toLowerCase().includes(q) ||
        t.family.toLowerCase().includes(q)
      )
    })
    const buckets: Record<string, typeof filtered> = {}
    for (const t of filtered) {
      const fam = t.family
      if (!buckets[fam]) buckets[fam] = []
      buckets[fam].push(t)
    }
    return buckets
  }, [tests, search])

  // When the active slug isn't in the filtered list, leave it untouched —
  // the right pane still shows it. But default to the first entry on
  // first render once `tests` arrives.
  useEffect(() => {
    if (!activeSlug && tests && tests.length > 0) {
      setActiveSlug(tests[0].slug)
    }
  }, [tests, activeSlug])

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

      {activeCat !== 'stat-tests' ? (
        <Card data-testid="learn-coming-soon">
          <CardHeader>
            <CardTitle className="text-[15px]">Coming soon</CardTitle>
          </CardHeader>
          <CardContent className="text-[13px] text-muted-foreground">
            The {CATEGORIES.find((c) => c.key === activeCat)?.label} reference
            section is not yet in this build. Phase 5b will add walkthroughs
            and checklists; Phase 5c adds economics and submission helpers.
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-[280px_1fr] gap-6 min-h-[60vh]">
          {/* Left: search + list */}
          <div className="space-y-3">
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search stat tests"
                data-testid="learn-search-input"
                aria-label="Search Learn entries"
                className="pl-8"
              />
            </div>
            <div
              data-testid="learn-entry-list"
              className="rounded-md border border-border bg-card"
            >
              {isLoading && (
                <div className="p-3 text-[12px] text-muted-foreground">
                  Loading reference content…
                </div>
              )}
              {!isLoading && Object.keys(grouped).length === 0 && (
                <div
                  data-testid="learn-no-results"
                  className="p-3 text-[12px] text-muted-foreground"
                >
                  No entries match "{search}".
                </div>
              )}
              {Object.entries(grouped)
                .sort(([a], [b]) => a.localeCompare(b))
                .map(([family, items]) => (
                  <div key={family} className="border-b border-border last:border-b-0">
                    <div className="px-3 pt-3 pb-1 text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
                      {family.replace(/_/g, ' ')}
                    </div>
                    {items.map((it) => {
                      const active = it.slug === activeSlug
                      return (
                        <button
                          key={it.slug}
                          data-testid={`learn-entry-${it.slug}`}
                          onClick={() => {
                            setActiveSlug(it.slug)
                            const next = new URLSearchParams(params)
                            next.set('slug', it.slug)
                            setParams(next, { replace: true })
                          }}
                          className={cn(
                            'flex w-full flex-col items-start gap-0.5 px-3 py-2 text-left transition-colors',
                            'text-[13px] hover:bg-muted/60',
                            active && 'bg-muted',
                          )}
                        >
                          <span className="font-medium leading-snug">{it.title}</span>
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
            {!detail ? (
              <Card>
                <CardContent className="py-8 text-[13px] text-muted-foreground">
                  Pick an entry from the list to read it here.
                </CardContent>
              </Card>
            ) : (
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
            )}
          </div>
        </div>
      )}
    </motion.div>
  )
}
