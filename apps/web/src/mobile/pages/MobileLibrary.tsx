/**
 * Phase M2.1 — Mobile Library.
 *
 * Replaces ``MobileLibraryPlaceholder`` with a full project-scoped
 * article list. Four moving parts:
 *
 *   1. A project picker row directly under the shell header. The
 *      active project's title is the tap target — touching it opens a
 *      ``BottomSheet`` listing every accessible project. Picking one
 *      writes the choice to the persisted ``useLastViewedProject``
 *      store so the next time the user opens the app they land on the
 *      same project.
 *   2. A ``MobileSearchBar`` underneath that filters the article list
 *      client-side (title + authors + journal).
 *   3. The article list itself. Each row shows title, authors, year,
 *      source badge + optional journal/DOI. Tapping a row navigates to
 *      the mobile reader.
 *   4. A floating "+" action button (FAB) anchored to the bottom-right
 *      above the tab bar that opens an action sheet with three ways to
 *      bring papers into the project:
 *        - Upload a PDF or DOCX (native file picker, ``articlesApi.upload``)
 *        - Add by DOI (``ingestApi.lookupDoi`` → ``importFromMetadata``)
 *        - Add by PubMed ID (``ingestApi.searchPubMed`` → ``importFromMetadata``)
 *
 * Offline: the article list query routes through ``cacheable()`` so the
 * library stays browseable when the laptop is unreachable. Writes
 * (upload / add-by-DOI / add-by-PMID) surface a toast asking the user
 * to reconnect if the network is down.
 *
 * The pull-to-refresh gesture is intentionally NOT implemented — it
 * was fiddly enough on iOS Safari to be a polish item (see DEFERRED).
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  BookOpen,
  ChevronDown,
  ChevronRight,
  FileUp,
  Hash,
  Library as LibraryIcon,
  Link2,
  Plus,
  WifiOff,
} from 'lucide-react'
import { useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  articlesApi,
  ingestApi,
  projectsApi,
  type Article,
} from '@/lib/api'
import { useLastViewedProject } from '@/lib/projectContext'
import { cn } from '@/lib/utils'

import { BottomSheet } from '../components/BottomSheet'
import { MobileEmpty } from '../components/MobileEmpty'
import { MobileSearchBar } from '../components/MobileSearchBar'
import { cacheable } from '../lib/offlineLearn'

type AddMode = 'upload' | 'doi' | 'pubmed' | null

const SOURCE_LABEL: Record<string, string> = {
  upload: 'Upload',
  doi: 'Crossref',
  pubmed: 'PubMed',
  ris: 'RIS',
  bibtex: 'BibTeX',
  manual: 'Manual',
}

export default function MobileLibrary() {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const lastProjectId = useLastViewedProject((s) => s.projectId)
  const setLastProject = useLastViewedProject((s) => s.set)

  const [search, setSearch] = useState('')
  const [picker, setPicker] = useState(false)
  const [actionSheet, setActionSheet] = useState(false)
  const [addMode, setAddMode] = useState<AddMode>(null)
  const [doiInput, setDoiInput] = useState('')
  const [pmidInput, setPmidInput] = useState('')
  const fileInputRef = useRef<HTMLInputElement | null>(null)

  const projects = useQuery({
    queryKey: ['projects', 'list'],
    queryFn: () => projectsApi.list(),
    staleTime: 60_000,
  })

  // Default to the first project when the persisted store is empty
  // (or points at a project the user no longer has access to).
  const activeProjectId = useMemo(() => {
    const list = projects.data ?? []
    if (list.length === 0) return null
    const valid = lastProjectId && list.some((p) => p.id === lastProjectId)
    return valid ? lastProjectId : list[0]?.id ?? null
  }, [projects.data, lastProjectId])

  const activeProject = useMemo(() => {
    if (!activeProjectId) return null
    return projects.data?.find((p) => p.id === activeProjectId) ?? null
  }, [projects.data, activeProjectId])

  const articles = useQuery({
    queryKey: ['mlib', 'articles', activeProjectId],
    queryFn: async () => {
      if (!activeProjectId) return { data: [] as Article[], offline: false }
      return cacheable<Article[]>(
        `mlib:articles:${activeProjectId}`,
        () => articlesApi.list(activeProjectId),
      )
    },
    enabled: !!activeProjectId,
    staleTime: 30_000,
  })

  const offline = articles.data?.offline ?? false
  const items = articles.data?.data ?? []

  const filtered = useMemo(() => {
    const needle = search.trim().toLowerCase()
    if (!needle) return items
    return items.filter((a) => {
      const hay = [
        a.title,
        a.journal ?? '',
        (a.authors ?? []).join(' '),
        a.doi ?? '',
        a.pmid ?? '',
      ]
        .join(' ')
        .toLowerCase()
      return hay.includes(needle)
    })
  }, [items, search])

  const uploadMutation = useMutation({
    mutationFn: async (file: File) => {
      if (!activeProjectId) throw new Error('Pick a project first')
      return articlesApi.upload(activeProjectId, file)
    },
    onSuccess: (resp) => {
      qc.invalidateQueries({ queryKey: ['mlib', 'articles', activeProjectId] })
      if (resp.duplicate_of) {
        toast.info(
          `"${resp.article.title.slice(0, 60)}" looks like a duplicate of an existing article.`,
        )
      } else {
        toast.success('Uploaded')
      }
      setActionSheet(false)
      setAddMode(null)
    },
    onError: (err) => {
      toast.error(err instanceof Error ? err.message : 'Upload failed')
    },
  })

  const addDoiMutation = useMutation({
    mutationFn: async (doi: string) => {
      if (!activeProjectId) throw new Error('Pick a project first')
      const meta = await ingestApi.lookupDoi(activeProjectId, doi)
      return ingestApi.importFromMetadata(activeProjectId, [meta])
    },
    onSuccess: (resp) => {
      qc.invalidateQueries({ queryKey: ['mlib', 'articles', activeProjectId] })
      if (resp.created.length > 0) toast.success('Article added from DOI')
      else if (resp.skipped_duplicates.length > 0)
        toast.info('That DOI is already in the project')
      else toast.message('No matching article found for that DOI')
      setAddMode(null)
      setDoiInput('')
    },
    onError: (err) => {
      toast.error(err instanceof Error ? err.message : 'DOI lookup failed')
    },
  })

  const addPmidMutation = useMutation({
    mutationFn: async (pmid: string) => {
      if (!activeProjectId) throw new Error('Pick a project first')
      // Reuse the PubMed search endpoint with a PMID-targeted query.
      const results = await ingestApi.searchPubMed(activeProjectId, pmid, 1)
      if (results.length === 0)
        throw new Error('PubMed returned no record for that ID')
      return ingestApi.importFromMetadata(activeProjectId, [results[0]])
    },
    onSuccess: (resp) => {
      qc.invalidateQueries({ queryKey: ['mlib', 'articles', activeProjectId] })
      if (resp.created.length > 0) toast.success('Article added from PubMed')
      else if (resp.skipped_duplicates.length > 0)
        toast.info('That article is already in the project')
      else toast.message('No matching article found for that PMID')
      setAddMode(null)
      setPmidInput('')
    },
    onError: (err) => {
      toast.error(err instanceof Error ? err.message : 'PubMed lookup failed')
    },
  })

  function onPickProject(pid: string) {
    setLastProject(pid)
    setPicker(false)
  }

  function openAddMode(mode: Exclude<AddMode, null>) {
    setActionSheet(false)
    if (mode === 'upload') {
      // Defer one tick so iOS Safari accepts the click as a gesture.
      setTimeout(() => fileInputRef.current?.click(), 50)
    } else {
      setAddMode(mode)
    }
  }

  function onFileChosen(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file) return
    uploadMutation.mutate(file)
  }

  return (
    <div className="flex min-h-full flex-col bg-background">
      {/* Project picker row — replaces a static page title. */}
      <div className="flex items-center justify-between gap-2 px-4 pt-4 pb-2">
        <button
          type="button"
          onClick={() => setPicker(true)}
          data-testid="mlib-project-trigger"
          className="flex min-w-0 items-center gap-1 text-left"
        >
          <div className="min-w-0">
            <div className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
              Project
            </div>
            <div className="flex min-w-0 items-center gap-1">
              <h2 className="truncate text-[18px] font-semibold tracking-tight">
                {activeProject?.title ?? 'No project'}
              </h2>
              <ChevronDown className="h-4 w-4 shrink-0 text-muted-foreground" />
            </div>
          </div>
        </button>
        {offline && (
          <Badge
            variant="outline"
            className="gap-1 border-amber-500/30 bg-amber-500/10 text-amber-700"
            data-testid="mlib-offline-badge"
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
          placeholder="Search articles"
          testId="mlib-search"
        />
      </div>

      <input
        type="file"
        accept=".pdf,.docx"
        ref={fileInputRef}
        onChange={onFileChosen}
        className="hidden"
        data-testid="mlib-file-input"
      />

      <div className="flex-1 pb-24">
        {articles.isLoading && (
          <div
            data-testid="mlib-loading"
            className="py-12 text-center text-[13px] text-muted-foreground"
          >
            Loading articles…
          </div>
        )}

        {!articles.isLoading && filtered.length === 0 && (
          <MobileEmpty
            icon={LibraryIcon}
            title={search ? 'No matches' : 'No articles yet'}
            subtitle={
              search
                ? 'Try a different search.'
                : 'Upload a PDF or add by DOI to get started.'
            }
            testId="mlib-empty"
          />
        )}

        {!articles.isLoading && filtered.length > 0 && (
          <div
            data-testid="mlib-list"
            className="mx-3 divide-y divide-border rounded-xl border border-border bg-card"
          >
            {filtered.map((a) => (
              <ArticleRow
                key={a.id}
                article={a}
                onOpen={() => navigate(`/m/reader/${a.id}`)}
              />
            ))}
          </div>
        )}
      </div>

      {/* Floating "+" button — bottom-right, above bottom tabs */}
      <button
        type="button"
        onClick={() => setActionSheet(true)}
        data-testid="mlib-fab"
        aria-label="Add article"
        disabled={!activeProjectId || uploadMutation.isPending}
        className={cn(
          'fixed right-4 z-30 inline-flex h-14 w-14 items-center justify-center rounded-full',
          'bg-primary text-primary-foreground shadow-lg shadow-primary/30',
          'active:scale-95 transition-transform',
          'disabled:opacity-50',
        )}
        style={{
          bottom: 'calc(64px + 16px + env(safe-area-inset-bottom))',
        }}
      >
        <Plus className="h-6 w-6" />
      </button>

      {/* Project picker */}
      <BottomSheet
        open={picker}
        onClose={() => setPicker(false)}
        title="Choose a project"
        snapPoints={['60%']}
      >
        {(projects.data ?? []).length === 0 && (
          <div className="py-6 text-center text-[13px] text-muted-foreground">
            No projects found. Create one on the desktop app first.
          </div>
        )}
        {(projects.data ?? []).map((p) => (
          <button
            key={p.id}
            type="button"
            data-testid={`mlib-project-${p.id}`}
            onClick={() => onPickProject(p.id)}
            className={cn(
              'flex w-full items-center justify-between border-b border-border last:border-b-0 py-3 text-left',
              p.id === activeProjectId && 'font-semibold',
            )}
          >
            <div className="min-w-0">
              <div className="truncate text-[14px]">{p.title}</div>
              <div className="mt-0.5 truncate text-[11px] text-muted-foreground">
                {p.study_type}
              </div>
            </div>
            <ChevronRight className="h-4 w-4 text-muted-foreground" />
          </button>
        ))}
      </BottomSheet>

      {/* Add action sheet */}
      <BottomSheet
        open={actionSheet}
        onClose={() => setActionSheet(false)}
        title="Add to library"
        snapPoints={['45%']}
      >
        <ActionRow
          icon={FileUp}
          title="Upload PDF or DOCX"
          subtitle="Pick a file from this device"
          onClick={() => openAddMode('upload')}
          testId="mlib-action-upload"
        />
        <ActionRow
          icon={Link2}
          title="Add by DOI"
          subtitle="Look up metadata from Crossref"
          onClick={() => openAddMode('doi')}
          testId="mlib-action-doi"
        />
        <ActionRow
          icon={Hash}
          title="Add by PubMed ID"
          subtitle="Pull citation + abstract from PubMed"
          onClick={() => openAddMode('pubmed')}
          testId="mlib-action-pubmed"
        />
      </BottomSheet>

      {/* DOI sheet */}
      <BottomSheet
        open={addMode === 'doi'}
        onClose={() => setAddMode(null)}
        title="Add by DOI"
        snapPoints={['40%']}
      >
        <form
          onSubmit={(e) => {
            e.preventDefault()
            const d = doiInput.trim()
            if (d) addDoiMutation.mutate(d)
          }}
          className="flex flex-col gap-3 pb-2"
        >
          <label className="text-[12px] text-muted-foreground" htmlFor="mlib-doi">
            Paste a DOI (e.g. 10.1056/NEJMoa2034577)
          </label>
          <input
            id="mlib-doi"
            data-testid="mlib-doi-input"
            type="text"
            inputMode="text"
            autoCapitalize="off"
            autoCorrect="off"
            placeholder="10.…"
            value={doiInput}
            onChange={(e) => setDoiInput(e.target.value)}
            className="h-11 rounded-lg border border-border bg-card px-3 text-[14px] focus:outline-none focus:ring-2 focus:ring-primary/40"
          />
          <Button
            type="submit"
            data-testid="mlib-doi-submit"
            disabled={!doiInput.trim() || addDoiMutation.isPending}
          >
            {addDoiMutation.isPending ? 'Looking up…' : 'Add'}
          </Button>
        </form>
      </BottomSheet>

      {/* PubMed sheet */}
      <BottomSheet
        open={addMode === 'pubmed'}
        onClose={() => setAddMode(null)}
        title="Add by PubMed ID"
        snapPoints={['40%']}
      >
        <form
          onSubmit={(e) => {
            e.preventDefault()
            const p = pmidInput.trim()
            if (p) addPmidMutation.mutate(p)
          }}
          className="flex flex-col gap-3 pb-2"
        >
          <label className="text-[12px] text-muted-foreground" htmlFor="mlib-pmid">
            Paste a PubMed ID (digits only)
          </label>
          <input
            id="mlib-pmid"
            data-testid="mlib-pmid-input"
            type="text"
            inputMode="numeric"
            pattern="[0-9]*"
            placeholder="e.g. 32325025"
            value={pmidInput}
            onChange={(e) => setPmidInput(e.target.value)}
            className="h-11 rounded-lg border border-border bg-card px-3 text-[14px] focus:outline-none focus:ring-2 focus:ring-primary/40"
          />
          <Button
            type="submit"
            data-testid="mlib-pmid-submit"
            disabled={!pmidInput.trim() || addPmidMutation.isPending}
          >
            {addPmidMutation.isPending ? 'Looking up…' : 'Add'}
          </Button>
        </form>
      </BottomSheet>
    </div>
  )
}

function ArticleRow({
  article,
  onOpen,
}: {
  article: Article
  onOpen: () => void
}) {
  const sourceLabel = SOURCE_LABEL[article.source] ?? article.source
  const authors = (article.authors ?? []).join(', ') || 'No authors listed'
  return (
    <button
      type="button"
      data-testid={`mlib-row-${article.id}`}
      onClick={onOpen}
      className="flex w-full flex-col gap-1 px-4 py-3 text-left transition-colors active:bg-muted/60 hover:bg-muted/40"
    >
      <div className="line-clamp-2 text-[14px] font-medium leading-snug">
        {article.title}
      </div>
      <div className="line-clamp-1 text-[12px] text-muted-foreground">
        {authors}
        {article.year ? ` · ${article.year}` : ''}
      </div>
      <div className="mt-1 flex flex-wrap items-center gap-1.5">
        <Badge variant="outline" className="text-[10px]">
          {sourceLabel}
        </Badge>
        {article.journal && (
          <Badge
            variant="outline"
            className="border-transparent bg-muted text-[10px] text-muted-foreground"
          >
            <BookOpen className="mr-1 h-3 w-3" />
            {article.journal}
          </Badge>
        )}
        {article.doi && (
          <span className="truncate text-[10px] text-muted-foreground">
            {article.doi}
          </span>
        )}
      </div>
    </button>
  )
}

function ActionRow({
  icon: Icon,
  title,
  subtitle,
  onClick,
  testId,
}: {
  icon: typeof FileUp
  title: string
  subtitle: string
  onClick: () => void
  testId: string
}) {
  return (
    <button
      type="button"
      data-testid={testId}
      onClick={onClick}
      className="flex w-full items-center gap-3 border-b border-border last:border-b-0 py-3 text-left active:bg-muted/40"
    >
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
        <Icon className="h-5 w-5" />
      </div>
      <div className="min-w-0 flex-1">
        <div className="text-[14px] font-semibold leading-tight">{title}</div>
        <div className="mt-0.5 text-[12px] text-muted-foreground">
          {subtitle}
        </div>
      </div>
      <ChevronRight className="h-4 w-4 text-muted-foreground" />
    </button>
  )
}
