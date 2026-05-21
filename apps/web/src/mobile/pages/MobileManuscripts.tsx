/**
 * Phase M3.1 — Mobile Manuscripts (project list).
 *
 * Replaces ``MobileManuscriptsPlaceholder``. The mobile Manuscripts tab
 * lists projects the user owns or has been granted access to; tapping
 * a card opens the read-friendly manuscript reader at
 * ``/m/manuscripts/:projectId`` (see ``MobileManuscriptReader``).
 *
 * The list is offline-readable: ``cacheable()`` writes the project
 * roster to IndexedDB on every successful fetch and re-serves it from
 * cache when the tailnet is unreachable. A small "Offline" badge in
 * the header signals when the data came from cache.
 *
 * A floating "+" FAB anchored above the bottom tabs opens a
 * BottomSheet with a title input + study-type select. Submitting calls
 * ``projectsApi.create`` and invalidates the list query. We default
 * the study_type to "Outcome Study" because it's the most permissive
 * shape and lets the user start writing immediately on a phone — they
 * can switch later from the desktop project settings panel.
 *
 * Empty state borrows ``MobileEmpty`` so the look matches the Library
 * tab. The card content (title + status badge + last-updated relative
 * time + abstract excerpt) is intentionally dense to keep the list
 * scannable on a 390px viewport.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ChevronRight, FileText, Plus, WifiOff } from 'lucide-react'
import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  frontmatterApi,
  projectsApi,
  type Project,
  type ProjectCreate,
} from '@/lib/api'
import { cn } from '@/lib/utils'

import { BottomSheet } from '../components/BottomSheet'
import { MobileEmpty } from '../components/MobileEmpty'
import { MobileSearchBar } from '../components/MobileSearchBar'
import { cacheable } from '../lib/offlineLearn'

type StudyType = ProjectCreate['study_type']

const STUDY_TYPES: { value: StudyType; label: string }[] = [
  { value: 'Outcome Study', label: 'Outcome Study' },
  { value: 'Before/After Intervention', label: 'Before/After Intervention' },
  { value: 'Risk Factor Analysis', label: 'Risk Factor Analysis' },
  { value: 'Group Comparison', label: 'Group Comparison' },
  { value: 'Prospective Cohort', label: 'Prospective Cohort' },
  { value: 'Retrospective Case Series', label: 'Retrospective Case Series' },
  { value: 'Systematic Review', label: 'Systematic Review' },
  { value: 'Randomised Controlled Trial', label: 'Randomised Controlled Trial' },
]

function relativeTime(iso: string): string {
  const then = new Date(iso).getTime()
  if (!Number.isFinite(then)) return ''
  const diffMs = Date.now() - then
  if (diffMs < 0) return 'just now'
  const minute = 60_000
  const hour = 60 * minute
  const day = 24 * hour
  if (diffMs < minute) return 'just now'
  if (diffMs < hour) return `${Math.floor(diffMs / minute)}m ago`
  if (diffMs < day) return `${Math.floor(diffMs / hour)}h ago`
  if (diffMs < 30 * day) return `${Math.floor(diffMs / day)}d ago`
  if (diffMs < 365 * day) return `${Math.floor(diffMs / (30 * day))}mo ago`
  return `${Math.floor(diffMs / (365 * day))}y ago`
}

export default function MobileManuscripts() {
  const navigate = useNavigate()
  const qc = useQueryClient()

  const [search, setSearch] = useState('')
  const [createOpen, setCreateOpen] = useState(false)
  const [titleDraft, setTitleDraft] = useState('')
  const [studyType, setStudyType] = useState<StudyType>('Outcome Study')

  const projectsQ = useQuery({
    queryKey: ['mmanu', 'projects'],
    queryFn: () =>
      cacheable<Project[]>('mmanu:projects', () => projectsApi.list()),
    staleTime: 30_000,
  })

  const offline = projectsQ.data?.offline ?? false
  const projects = projectsQ.data?.data ?? []

  // Fetch abstract excerpts from each project's frontmatter in
  // parallel. We don't block the list on these — the rows render
  // without an excerpt until the per-project frontmatter resolves.
  const abstractQ = useQuery({
    queryKey: ['mmanu', 'abstracts', projects.map((p) => p.id).join(',')],
    queryFn: async () => {
      const entries = await Promise.allSettled(
        projects.map(async (p) => {
          const fm = await frontmatterApi.frontmatter.get(p.id)
          // Prefer the structured background field as a preview; fall
          // back to the joined sections if structured mode is off.
          const sa = fm.structured_abstract
          const combined = [sa.background, sa.methods, sa.results, sa.conclusions]
            .filter((s) => s && s.trim().length > 0)
            .join(' ')
          return [p.id, combined.trim()] as const
        }),
      )
      const out: Record<string, string> = {}
      for (const e of entries) {
        if (e.status === 'fulfilled') out[e.value[0]] = e.value[1]
      }
      return out
    },
    enabled: projects.length > 0,
    staleTime: 60_000,
  })

  const filtered = useMemo(() => {
    const needle = search.trim().toLowerCase()
    if (!needle) return projects
    return projects.filter((p) =>
      [p.title, p.study_type, p.target_journal ?? ''].join(' ').toLowerCase().includes(needle),
    )
  }, [projects, search])

  const createMutation = useMutation({
    mutationFn: async (body: ProjectCreate) => projectsApi.create(body),
    onSuccess: (p) => {
      qc.invalidateQueries({ queryKey: ['mmanu', 'projects'] })
      toast.success('Project created')
      setCreateOpen(false)
      setTitleDraft('')
      setStudyType('Outcome Study')
      navigate(`/m/manuscripts/${p.id}`)
    },
    onError: (err) => {
      if (!navigator.onLine) {
        toast.error('Offline — connect to laptop to create a project')
      } else {
        toast.error(err instanceof Error ? err.message : 'Create failed')
      }
    },
  })

  function onSubmitCreate(e: React.FormEvent) {
    e.preventDefault()
    const t = titleDraft.trim()
    if (!t) return
    createMutation.mutate({ title: t, study_type: studyType })
  }

  return (
    <div className="flex min-h-full flex-col bg-background">
      <div className="flex items-center justify-between gap-2 px-4 pt-4 pb-2">
        <div className="min-w-0">
          <div className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
            Manuscripts
          </div>
          <h2 className="truncate text-[18px] font-semibold tracking-tight">
            Your projects
          </h2>
        </div>
        {offline && (
          <Badge
            variant="outline"
            className="gap-1 border-amber-500/30 bg-amber-500/10 text-amber-700"
            data-testid="mmanu-offline-badge"
          >
            <WifiOff className="h-3 w-3" />
            Offline
          </Badge>
        )}
      </div>

      <div className="px-3 pt-1 pb-3">
        <MobileSearchBar
          value={search}
          onChange={setSearch}
          placeholder="Search projects"
          testId="mmanu-search"
        />
      </div>

      <div className="flex-1 pb-24">
        {projectsQ.isLoading && (
          <div
            data-testid="mmanu-loading"
            className="py-12 text-center text-[13px] text-muted-foreground"
          >
            Loading projects…
          </div>
        )}

        {!projectsQ.isLoading && filtered.length === 0 && (
          <MobileEmpty
            icon={FileText}
            title={search ? 'No matches' : 'No manuscripts yet'}
            subtitle={
              search
                ? 'Try a different search.'
                : 'Create one to start writing.'
            }
            testId="mmanu-empty"
          />
        )}

        {!projectsQ.isLoading && filtered.length > 0 && (
          <div
            data-testid="mmanu-list"
            className="mx-3 flex flex-col gap-2"
          >
            {filtered.map((p) => (
              <ProjectCard
                key={p.id}
                project={p}
                abstract={abstractQ.data?.[p.id] ?? ''}
                onOpen={() => navigate(`/m/manuscripts/${p.id}`)}
              />
            ))}
          </div>
        )}
      </div>

      <button
        type="button"
        onClick={() => setCreateOpen(true)}
        data-testid="mmanu-fab"
        aria-label="New project"
        className={cn(
          'fixed right-4 z-30 inline-flex h-14 w-14 items-center justify-center rounded-full',
          'bg-primary text-primary-foreground shadow-lg shadow-primary/30',
          'active:scale-95 transition-transform',
        )}
        style={{
          bottom: 'calc(64px + 16px + env(safe-area-inset-bottom))',
        }}
      >
        <Plus className="h-6 w-6" />
      </button>

      <BottomSheet
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        title="New project"
        snapPoints={['65%']}
      >
        <form
          onSubmit={onSubmitCreate}
          className="flex flex-col gap-3 pb-2"
          data-testid="mmanu-create-sheet"
        >
          <label className="text-[12px] text-muted-foreground" htmlFor="mmanu-title">
            Title
          </label>
          <input
            id="mmanu-title"
            data-testid="mmanu-title-input"
            type="text"
            value={titleDraft}
            onChange={(e) => setTitleDraft(e.target.value)}
            placeholder="e.g. Hip replacement outcomes 2026"
            className="h-11 rounded-lg border border-border bg-card px-3 text-[14px] focus:outline-none focus:ring-2 focus:ring-primary/40"
            autoFocus
          />

          <label className="mt-1 text-[12px] text-muted-foreground" htmlFor="mmanu-study-type">
            Study type
          </label>
          <select
            id="mmanu-study-type"
            data-testid="mmanu-study-type"
            value={studyType}
            onChange={(e) => setStudyType(e.target.value as StudyType)}
            className="h-11 rounded-lg border border-border bg-card px-3 text-[14px] focus:outline-none focus:ring-2 focus:ring-primary/40"
          >
            {STUDY_TYPES.map((t) => (
              <option key={t.value} value={t.value}>
                {t.label}
              </option>
            ))}
          </select>

          <Button
            type="submit"
            data-testid="mmanu-create-submit"
            disabled={!titleDraft.trim() || createMutation.isPending}
            className="mt-2"
          >
            {createMutation.isPending ? 'Creating…' : 'Create project'}
          </Button>
        </form>
      </BottomSheet>
    </div>
  )
}

function ProjectCard({
  project,
  abstract,
  onOpen,
}: {
  project: Project
  abstract: string
  onOpen: () => void
}) {
  return (
    <button
      type="button"
      data-testid={`mmanu-row-${project.id}`}
      onClick={onOpen}
      className="flex w-full flex-col gap-1.5 rounded-xl border border-border bg-card px-4 py-3 text-left transition-colors active:bg-muted/60 hover:bg-muted/40"
    >
      <div className="flex items-start justify-between gap-2">
        <div className="line-clamp-2 flex-1 text-[14px] font-medium leading-snug">
          {project.title}
        </div>
        <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground" />
      </div>
      <div className="flex flex-wrap items-center gap-1.5 text-[11px] text-muted-foreground">
        <Badge variant="outline" className="text-[10px]">
          {project.study_type}
        </Badge>
        <span>·</span>
        <span data-testid={`mmanu-updated-${project.id}`}>
          Updated {relativeTime(project.updated_at)}
        </span>
      </div>
      {abstract && (
        <div
          className="line-clamp-2 text-[12px] text-muted-foreground"
          data-testid={`mmanu-abstract-${project.id}`}
        >
          {abstract}
        </div>
      )}
    </button>
  )
}
