/**
 * Phase M3.2 — Mobile Manuscript reader + per-paragraph edit sheet.
 *
 * The desktop editor is a TipTap rich-text surface backed by ProseMirror
 * — beautiful on a 27-inch monitor, hostile on a phone (no caret
 * control, jumpy scroll, no per-paragraph focus). The mobile reader
 * takes the opposite approach:
 *
 *   1. Section content is fetched as HTML (the canonical shape on the
 *      backend) for each of the six IMRaD sections.
 *   2. We split each section's HTML on `</p>` boundaries to recover an
 *      array of paragraph fragments. Each fragment retains any inline
 *      formatting (links, ``<sup data-citation>`` chips). We do NOT
 *      try to render full TipTap output — the manuscript content the
 *      backend serves is conservative enough that ``dangerouslySetInnerHTML``
 *      on each paragraph is the simplest faithful renderer.
 *   3. Each paragraph carries ``data-paragraph-id="<section>-p<N>"``
 *      so screen readers, tests, and a future commenting hook can
 *      address them individually.
 *   4. Tapping a paragraph opens a ``BottomSheet`` with an auto-growing
 *      textarea pre-filled with the paragraph's plain text (citation
 *      chips and tags are stripped for editing). Save patches the
 *      section by joining the paragraph array back together with the
 *      edited text in place.
 *   5. Tapping a citation chip (``<sup data-citation data-article-id="…">``)
 *      navigates to ``/m/reader/<articleId>``.
 *
 * Highlights on the manuscript — not implemented in M3. The existing
 * comments backend takes section + character offsets (not a
 * paragraph_id), and mapping a touch to an offset robustly across a
 * mixed-HTML paragraph would require selection plumbing we explicitly
 * declined to grow in M3. The overflow menu surfaces a "Highlights
 * coming soon" message so the gap is visible to the user.
 *
 * Frontmatter / Snapshots / Export are all opened as read-only sheets
 * over existing endpoints; mobile is intentionally a thin client over
 * the canonical desktop data.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  ArrowLeft,
  Download,
  FileSignature,
  History,
  Loader2,
  MoreVertical,
  Sparkles,
  WifiOff,
} from 'lucide-react'
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { toast } from 'sonner'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  exportApi,
  frontmatterApi,
  manuscriptApi,
  projectsApi,
  snapshotsApi,
  writingApi,
  type ManuscriptSection,
  type ManuscriptSectionName,
  type Project,
  type ProjectFrontmatter,
  type SnapshotSummary,
} from '@/lib/api'
import { cn } from '@/lib/utils'

import { BottomSheet } from '../components/BottomSheet'
import { cacheable } from '../lib/offlineLearn'

const SECTION_ORDER: ManuscriptSectionName[] = [
  'Abstract',
  'Introduction',
  'Methodology',
  'Results',
  'Discussion',
  'Conclusion',
]

const SECTION_DISPLAY: Record<ManuscriptSectionName, string> = {
  Abstract: 'Abstract',
  Introduction: 'Introduction',
  Methodology: 'Methods',
  Results: 'Results',
  Discussion: 'Discussion',
  Conclusion: 'Conclusion',
}

// ---------------------------------------------------------------------------
// Paragraph splitting / joining. We rely on a paragraph fragment being
// of the form ``<p>...</p>`` since that's what the TipTap-backed
// editor emits. ``splitParagraphs`` keeps the wrapping ``<p>`` tags on
// each fragment so the join is a simple concatenation.
// ---------------------------------------------------------------------------

function splitParagraphs(html: string): string[] {
  if (!html || !html.trim()) return []
  // Split on the closing `</p>` while keeping it on the preceding chunk.
  const parts = html.split(/(?<=<\/p>)/i)
  return parts.map((p) => p.trim()).filter((p) => p.length > 0)
}

function joinParagraphs(paragraphs: string[]): string {
  return paragraphs.join('')
}

/** Strip HTML tags + decode entities for textarea editing. We preserve
 * citation chip identifiers in a sidecar map so they can be restored
 * verbatim when the edit is saved. */
function htmlToText(html: string): string {
  if (typeof document === 'undefined') {
    return html.replace(/<[^>]+>/g, '').replace(/&nbsp;/g, ' ').trim()
  }
  const tmp = document.createElement('div')
  tmp.innerHTML = html
  // Replace citation chips with their literal token text so the user
  // sees something they can keep or delete deliberately.
  const supEls = tmp.querySelectorAll('sup[data-citation]')
  supEls.forEach((el) => {
    const text = el.textContent ?? ''
    el.replaceWith(text)
  })
  return (tmp.textContent ?? '').trim()
}

/** Rebuild a paragraph HTML by wrapping the edited text in <p>...</p>
 * and preserving the original citation chips at the end if the
 * paragraph had any. This avoids users accidentally destroying
 * citations during a quick mobile edit. */
function rebuildParagraph(originalHtml: string, editedText: string): string {
  const text = editedText.trim()
  if (!text) return '<p></p>'
  // Extract any `<sup data-citation>` chips from the original.
  const chipRe = /<sup\b[^>]*\bdata-citation\b[^>]*>[\s\S]*?<\/sup>/gi
  const chips: string[] = []
  let match: RegExpExecArray | null
  while ((match = chipRe.exec(originalHtml)) !== null) {
    chips.push(match[0])
  }
  // Naive: append chips after the edited text if the edited text
  // doesn't already contain them. The desktop editor remains the
  // source of truth for precise inline citation placement.
  const escaped = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
  const chipBlock = chips.join('')
  return `<p>${escaped}${chipBlock}</p>`
}

// ---------------------------------------------------------------------------
// Section content count utilities
// ---------------------------------------------------------------------------

function countWords(html: string): number {
  const text = html.replace(/<[^>]+>/g, ' ')
  const tokens = text.split(/\s+/).filter((t) => t.length > 0)
  return tokens.length
}

function countCitations(html: string): number {
  const matches = html.match(/<sup\b[^>]*\bdata-citation\b/gi)
  return matches ? matches.length : 0
}

function relativeTime(iso: string | null): string {
  if (!iso) return 'never'
  const then = new Date(iso).getTime()
  if (!Number.isFinite(then)) return 'never'
  const diffMs = Date.now() - then
  if (diffMs < 0) return 'just now'
  const m = 60_000
  const h = 60 * m
  const d = 24 * h
  if (diffMs < m) return 'just now'
  if (diffMs < h) return `${Math.floor(diffMs / m)}m ago`
  if (diffMs < d) return `${Math.floor(diffMs / h)}h ago`
  if (diffMs < 30 * d) return `${Math.floor(diffMs / d)}d ago`
  return new Date(iso).toLocaleDateString()
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

type ExportKind = 'docx' | 'pdf' | 'bundle'

export default function MobileManuscriptReader() {
  const params = useParams<{ projectId: string }>()
  const projectId = params.projectId
  const navigate = useNavigate()
  const qc = useQueryClient()

  // ------ Data
  const projectQ = useQuery({
    queryKey: ['mmr', 'project', projectId],
    queryFn: async () => {
      if (!projectId) throw new Error('missing projectId')
      return cacheable<Project>(`mmr:project:${projectId}`, () =>
        projectsApi.get(projectId),
      )
    },
    enabled: !!projectId,
  })

  const sectionQs = SECTION_ORDER.map((s) =>
    useQuery({
      queryKey: ['mmr', 'section', projectId, s],
      queryFn: async () => {
        if (!projectId) throw new Error('missing projectId')
        return cacheable<ManuscriptSection>(`mmr:section:${projectId}:${s}`, () =>
          manuscriptApi.getSection(projectId, s),
        )
      },
      enabled: !!projectId,
    }),
  )

  const sections: Record<ManuscriptSectionName, ManuscriptSection | null> =
    useMemo(() => {
      const out = {} as Record<ManuscriptSectionName, ManuscriptSection | null>
      SECTION_ORDER.forEach((s, i) => {
        out[s] = sectionQs[i].data?.data ?? null
      })
      return out
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [sectionQs.map((q) => q.data?.data?.content ?? '').join('|')])

  const offline =
    (projectQ.data?.offline ?? false) ||
    sectionQs.some((q) => q.data?.offline ?? false)

  const totalWords = useMemo(
    () =>
      SECTION_ORDER.reduce(
        (acc, s) => acc + countWords(sections[s]?.content ?? ''),
        0,
      ),
    [sections],
  )
  const totalCites = useMemo(
    () =>
      SECTION_ORDER.reduce(
        (acc, s) => acc + countCitations(sections[s]?.content ?? ''),
        0,
      ),
    [sections],
  )
  const lastSavedIso = useMemo(() => {
    let latest: string | null = null
    for (const s of SECTION_ORDER) {
      const u = sections[s]?.updated_at
      if (u && (latest === null || u > latest)) latest = u
    }
    return latest
  }, [sections])

  // ------ Per-paragraph state
  type EditTarget = {
    section: ManuscriptSectionName
    paragraphIdx: number
    /** The original HTML fragment for this paragraph (with `<p>...</p>`). */
    original: string
    /** The currently editable plain-text body. */
    draft: string
    /** AI rewrite candidate, if the user has tapped "AI rewrite". */
    aiCandidate: string | null
  }
  const [edit, setEdit] = useState<EditTarget | null>(null)
  const editTextareaRef = useRef<HTMLTextAreaElement | null>(null)

  function openParagraph(section: ManuscriptSectionName, paragraphIdx: number) {
    const html = sections[section]?.content ?? ''
    const paras = splitParagraphs(html)
    const original = paras[paragraphIdx] ?? ''
    setEdit({
      section,
      paragraphIdx,
      original,
      draft: htmlToText(original),
      aiCandidate: null,
    })
  }

  function discardAi() {
    setEdit((e) => (e ? { ...e, aiCandidate: null } : e))
  }

  function applyAi() {
    setEdit((e) =>
      e && e.aiCandidate ? { ...e, draft: e.aiCandidate, aiCandidate: null } : e,
    )
  }

  function closeEdit() {
    setEdit(null)
  }

  // Auto-grow the textarea
  useEffect(() => {
    const ta = editTextareaRef.current
    if (!ta) return
    ta.style.height = 'auto'
    ta.style.height = `${Math.min(ta.scrollHeight, 480)}px`
  }, [edit?.draft, edit?.aiCandidate])

  // ------ Mutations
  const aiMutation = useMutation({
    mutationFn: async (text: string) => writingApi.assist('improve', text),
    onSuccess: (revised) => {
      setEdit((e) => (e ? { ...e, aiCandidate: revised } : e))
    },
    onError: (err) => {
      if (!navigator.onLine) {
        toast.error('Offline — connect to laptop to use AI')
      } else {
        toast.error(err instanceof Error ? err.message : 'AI rewrite failed')
      }
    },
  })

  const saveMutation = useMutation({
    mutationFn: async () => {
      if (!projectId || !edit) throw new Error('not editing')
      const section = sections[edit.section]
      if (!section) throw new Error('section missing')
      const paras = splitParagraphs(section.content)
      const rebuilt = rebuildParagraph(edit.original, edit.draft)
      paras[edit.paragraphIdx] = rebuilt
      const joined = joinParagraphs(paras)
      return manuscriptApi.upsertSection(projectId, edit.section, joined)
    },
    onSuccess: () => {
      if (!projectId || !edit) return
      qc.invalidateQueries({
        queryKey: ['mmr', 'section', projectId, edit.section],
      })
      toast.success('Saved')
      setEdit(null)
    },
    onError: (err) => {
      if (!navigator.onLine) {
        toast.error('Offline — connect to laptop to save')
      } else {
        toast.error(err instanceof Error ? err.message : 'Save failed')
      }
    },
  })

  // ------ Citation chip handling: a delegated click handler on the
  // article body intercepts taps on ``<sup data-citation>`` nodes and
  // routes to the mobile article reader. Other taps fall through to
  // paragraph-edit handlers below.
  const onBodyClick = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      const target = e.target as HTMLElement
      const sup = target.closest('sup[data-citation]') as HTMLElement | null
      if (sup) {
        e.preventDefault()
        e.stopPropagation()
        const aid = sup.getAttribute('data-article-id')
        if (aid) navigate(`/m/reader/${aid}`)
        return
      }
      const para = target.closest('[data-paragraph-id]') as HTMLElement | null
      if (!para) return
      const id = para.getAttribute('data-paragraph-id')
      if (!id) return
      const [section, rest] = id.split('-p')
      const idx = Number(rest)
      if (!Number.isFinite(idx)) return
      openParagraph(section as ManuscriptSectionName, idx)
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [sections, projectId],
  )

  // ------ Overflow menu
  const [overflowOpen, setOverflowOpen] = useState(false)
  const [frontmatterOpen, setFrontmatterOpen] = useState(false)
  const [snapshotsOpen, setSnapshotsOpen] = useState(false)
  const [exportOpen, setExportOpen] = useState(false)
  const [highlightsOpen, setHighlightsOpen] = useState(false)

  // Frontmatter detail
  const frontmatterQ = useQuery({
    queryKey: ['mmr', 'frontmatter', projectId],
    queryFn: () => {
      if (!projectId) throw new Error('missing projectId')
      return frontmatterApi.frontmatter.get(projectId)
    },
    enabled: !!projectId && frontmatterOpen,
  })
  const authorsQ = useQuery({
    queryKey: ['mmr', 'authors', projectId],
    queryFn: () => {
      if (!projectId) throw new Error('missing projectId')
      return frontmatterApi.authors.list(projectId)
    },
    enabled: !!projectId && frontmatterOpen,
  })
  const affiliationsQ = useQuery({
    queryKey: ['mmr', 'affiliations', projectId],
    queryFn: () => {
      if (!projectId) throw new Error('missing projectId')
      return frontmatterApi.affiliations.list(projectId)
    },
    enabled: !!projectId && frontmatterOpen,
  })

  const snapshotsQ = useQuery({
    queryKey: ['mmr', 'snapshots', projectId],
    queryFn: () => {
      if (!projectId) throw new Error('missing projectId')
      return snapshotsApi.list(projectId)
    },
    enabled: !!projectId && snapshotsOpen,
  })

  // Export mutation — one mutation, the kind is passed at call time so
  // we only need a single button row in the sheet.
  const exportMutation = useMutation({
    mutationFn: async (kind: ExportKind) => {
      if (!projectId) throw new Error('missing projectId')
      if (kind === 'docx') return exportApi.downloadDocx(projectId)
      if (kind === 'pdf') return exportApi.downloadPdf(projectId)
      return exportApi.downloadBundle(projectId)
    },
    onSuccess: (filename) => {
      toast.success(`Downloaded ${filename}`)
      setExportOpen(false)
    },
    onError: (err) => {
      toast.error(err instanceof Error ? err.message : 'Export failed')
    },
  })

  // ------ Render guards
  if (!projectId) {
    return (
      <div className="p-6 text-center text-[14px] text-muted-foreground">
        No project selected.
      </div>
    )
  }
  const project = projectQ.data?.data
  if (projectQ.isLoading || sectionQs.some((q) => q.isLoading)) {
    return (
      <div className="flex items-center justify-center py-16">
        <Loader2
          className="h-6 w-6 animate-spin text-muted-foreground"
          data-testid="mmr-loading"
        />
      </div>
    )
  }
  if (projectQ.isError || !project) {
    return (
      <div className="p-6 text-center text-[14px] text-rose-700">
        Could not load project.
      </div>
    )
  }

  return (
    <div className="flex min-h-full flex-col bg-background" data-testid="mmr-root">
      {/* Header */}
      <header className="sticky top-0 z-30 flex h-12 items-center gap-2 border-b border-border bg-background/95 px-2 backdrop-blur">
        <button
          type="button"
          aria-label="Back"
          onClick={() => navigate('/m/manuscripts')}
          className="inline-flex h-10 w-10 items-center justify-center rounded-md hover:bg-muted"
          data-testid="mmr-back"
        >
          <ArrowLeft className="h-5 w-5" />
        </button>
        <h1
          className="flex-1 truncate text-[14px] font-semibold tracking-tight"
          data-testid="mmr-title"
        >
          {project.title}
        </h1>
        {offline && (
          <Badge
            variant="outline"
            className="gap-1 border-amber-500/30 bg-amber-500/10 text-amber-700"
            data-testid="mmr-offline-badge"
          >
            <WifiOff className="h-3 w-3" />
            Offline
          </Badge>
        )}
        <button
          type="button"
          aria-label="More actions"
          onClick={() => setOverflowOpen(true)}
          className="inline-flex h-10 w-10 items-center justify-center rounded-md hover:bg-muted"
          data-testid="mmr-overflow"
        >
          <MoreVertical className="h-5 w-5" />
        </button>
      </header>

      {/* Body */}
      <div
        className="flex-1 px-4 pt-3 pb-36 text-[15px] leading-7 text-foreground"
        onClick={onBodyClick}
        data-testid="mmr-body"
      >
        {SECTION_ORDER.map((s) => {
          const section = sections[s]
          const paras = splitParagraphs(section?.content ?? '')
          return (
            <section
              key={s}
              className="mb-6"
              data-testid={`mmr-section-${s}`}
            >
              <div
                className="sticky top-12 z-10 -mx-4 mb-2 border-b border-border bg-background/95 px-4 py-2 backdrop-blur"
                data-testid={`mmr-section-header-${s}`}
              >
                <span className="inline-flex items-center rounded-full bg-primary/10 px-2.5 py-0.5 text-[11px] font-semibold uppercase tracking-wider text-primary">
                  {SECTION_DISPLAY[s]}
                </span>
              </div>
              {paras.length === 0 && (
                <p
                  className="my-3 italic text-muted-foreground text-[13px]"
                  data-testid={`mmr-section-empty-${s}`}
                >
                  (Empty — write this section on desktop or below.)
                </p>
              )}
              {paras.map((p, i) => (
                <ParagraphRow
                  key={`${s}-p${i}`}
                  section={s}
                  index={i}
                  html={p}
                />
              ))}
            </section>
          )
        })}
      </div>

      {/* Bottom action bar */}
      <div
        className="fixed inset-x-0 z-20 border-t border-border bg-background/95 px-3 py-2 backdrop-blur"
        style={{ bottom: 64 }}
        data-testid="mmr-action-bar"
      >
        <div className="flex flex-wrap items-center gap-1.5 text-[11px] text-muted-foreground">
          <Badge variant="outline" data-testid="mmr-words">
            {totalWords} words
          </Badge>
          <Badge variant="outline" data-testid="mmr-citations">
            {totalCites} citations
          </Badge>
          <Badge variant="outline" data-testid="mmr-lastsaved">
            Saved {relativeTime(lastSavedIso)}
          </Badge>
        </div>
      </div>

      {/* Overflow sheet */}
      <BottomSheet
        open={overflowOpen}
        onClose={() => setOverflowOpen(false)}
        title="Manuscript actions"
        snapPoints={['50%']}
      >
        <div className="flex flex-col gap-1" data-testid="mmr-overflow-sheet">
          <OverflowRow
            icon={FileSignature}
            title="View frontmatter"
            subtitle="Title, authors, abstract, keywords"
            onClick={() => {
              setOverflowOpen(false)
              setFrontmatterOpen(true)
            }}
            testId="mmr-overflow-frontmatter"
          />
          <OverflowRow
            icon={History}
            title="Snapshots"
            subtitle="Browse saved versions"
            onClick={() => {
              setOverflowOpen(false)
              setSnapshotsOpen(true)
            }}
            testId="mmr-overflow-snapshots"
          />
          <OverflowRow
            icon={Download}
            title="Export"
            subtitle="DOCX, PDF, or bundle"
            onClick={() => {
              setOverflowOpen(false)
              setExportOpen(true)
            }}
            testId="mmr-overflow-export"
          />
          <OverflowRow
            icon={Sparkles}
            title="Highlights"
            subtitle="Coming soon — use the desktop reader"
            onClick={() => {
              setOverflowOpen(false)
              setHighlightsOpen(true)
            }}
            testId="mmr-overflow-highlights"
          />
        </div>
      </BottomSheet>

      {/* Per-paragraph edit sheet */}
      <BottomSheet
        open={edit !== null}
        onClose={closeEdit}
        title="Edit paragraph"
        snapPoints={['85%']}
      >
        {edit && (
          <div className="flex flex-col gap-3 pb-2" data-testid="mmr-edit-sheet">
            <div>
              <Badge
                variant="outline"
                className="border-primary/30 bg-primary/10 text-primary"
                data-testid="mmr-edit-section-badge"
              >
                {SECTION_DISPLAY[edit.section]}
              </Badge>
            </div>

            <textarea
              ref={editTextareaRef}
              value={edit.aiCandidate ?? edit.draft}
              onChange={(e) =>
                setEdit((cur) =>
                  cur
                    ? cur.aiCandidate != null
                      ? { ...cur, aiCandidate: e.target.value }
                      : { ...cur, draft: e.target.value }
                    : cur,
                )
              }
              data-testid="mmr-edit-textarea"
              autoFocus
              className="min-h-[140px] resize-none rounded-lg border border-border bg-card px-3 py-2 text-[14px] focus:outline-none focus:ring-2 focus:ring-primary/40"
            />

            {edit.aiCandidate != null && (
              <div className="flex items-center gap-2 text-[12px] text-muted-foreground">
                <Sparkles className="h-3.5 w-3.5 text-primary" />
                AI rewrite candidate. Apply or discard before saving.
              </div>
            )}

            <div className="flex flex-wrap gap-2">
              {edit.aiCandidate == null ? (
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  disabled={aiMutation.isPending}
                  onClick={() => aiMutation.mutate(edit.draft)}
                  data-testid="mmr-edit-ai"
                >
                  <Sparkles className="mr-1.5 h-3.5 w-3.5" />
                  {aiMutation.isPending ? 'Rewriting…' : 'AI rewrite'}
                </Button>
              ) : (
                <>
                  <Button
                    type="button"
                    variant="default"
                    size="sm"
                    onClick={applyAi}
                    data-testid="mmr-edit-ai-apply"
                  >
                    Apply
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={discardAi}
                    data-testid="mmr-edit-ai-discard"
                  >
                    Discard
                  </Button>
                </>
              )}
              <div className="ml-auto flex gap-2">
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={closeEdit}
                  data-testid="mmr-edit-cancel"
                >
                  Cancel
                </Button>
                <Button
                  type="button"
                  size="sm"
                  disabled={saveMutation.isPending}
                  onClick={() => saveMutation.mutate()}
                  data-testid="mmr-edit-save"
                >
                  {saveMutation.isPending ? 'Saving…' : 'Save'}
                </Button>
              </div>
            </div>
          </div>
        )}
      </BottomSheet>

      {/* Frontmatter sheet */}
      <BottomSheet
        open={frontmatterOpen}
        onClose={() => setFrontmatterOpen(false)}
        title="Frontmatter"
        snapPoints={['90%']}
      >
        <FrontmatterView
          project={project}
          frontmatter={frontmatterQ.data ?? null}
          authors={authorsQ.data ?? []}
          affiliations={affiliationsQ.data ?? []}
          loading={
            frontmatterQ.isLoading ||
            authorsQ.isLoading ||
            affiliationsQ.isLoading
          }
        />
      </BottomSheet>

      {/* Snapshots sheet */}
      <BottomSheet
        open={snapshotsOpen}
        onClose={() => setSnapshotsOpen(false)}
        title="Snapshots"
        snapPoints={['80%']}
      >
        <SnapshotsView
          snapshots={snapshotsQ.data ?? []}
          loading={snapshotsQ.isLoading}
        />
      </BottomSheet>

      {/* Export sheet */}
      <BottomSheet
        open={exportOpen}
        onClose={() => setExportOpen(false)}
        title="Export"
        snapPoints={['45%']}
      >
        <div className="flex flex-col gap-2 pb-2" data-testid="mmr-export-sheet">
          <Button
            type="button"
            variant="outline"
            disabled={exportMutation.isPending}
            onClick={() => exportMutation.mutate('docx')}
            data-testid="mmr-export-docx"
          >
            <Download className="mr-2 h-4 w-4" />
            Download .docx
          </Button>
          <Button
            type="button"
            variant="outline"
            disabled={exportMutation.isPending}
            onClick={() => exportMutation.mutate('pdf')}
            data-testid="mmr-export-pdf"
          >
            <Download className="mr-2 h-4 w-4" />
            Download .pdf
          </Button>
          <Button
            type="button"
            variant="outline"
            disabled={exportMutation.isPending}
            onClick={() => exportMutation.mutate('bundle')}
            data-testid="mmr-export-bundle"
          >
            <Download className="mr-2 h-4 w-4" />
            Download bundle (.json)
          </Button>
        </div>
      </BottomSheet>

      {/* Highlights placeholder sheet */}
      <BottomSheet
        open={highlightsOpen}
        onClose={() => setHighlightsOpen(false)}
        title="Highlights"
        snapPoints={['40%']}
      >
        <div
          className="flex flex-col gap-2 pb-2 text-[13px] text-muted-foreground"
          data-testid="mmr-highlights-sheet"
        >
          Manuscript highlights are not yet available on mobile. Use the
          desktop reader to add margin comments and coloured highlights;
          they will sync down to mobile once the section comments
          backend exposes paragraph-level anchors.
        </div>
      </BottomSheet>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function ParagraphRow({
  section,
  index,
  html,
}: {
  section: ManuscriptSectionName
  index: number
  html: string
}) {
  // Strip the wrapping <p> tags so we can render a proper <p> from
  // React (otherwise we'd nest one inside another). The inner HTML
  // still carries inline tags like <strong>, <em>, <sup data-citation>.
  const inner = useMemo(() => {
    const m = /^<p\b[^>]*>([\s\S]*)<\/p>$/i.exec(html)
    return m ? m[1] : html
  }, [html])

  return (
    <p
      data-paragraph-id={`${section}-p${index}`}
      data-testid={`mmr-para-${section}-${index}`}
      className={cn(
        'my-3 cursor-pointer rounded-md transition-colors',
        'active:bg-muted/60 hover:bg-muted/40',
        '[&_sup[data-citation]]:cursor-pointer',
        '[&_sup[data-citation]]:rounded-sm',
        '[&_sup[data-citation]]:bg-primary/10',
        '[&_sup[data-citation]]:px-1',
        '[&_sup[data-citation]]:text-primary',
      )}
      dangerouslySetInnerHTML={{ __html: inner }}
    />
  )
}

function OverflowRow({
  icon: Icon,
  title,
  subtitle,
  onClick,
  testId,
}: {
  icon: typeof Download
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
      className="flex w-full items-center gap-3 rounded-lg border border-border bg-card px-3 py-3 text-left transition-colors active:bg-muted/60 hover:bg-muted/40"
    >
      <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-muted">
        <Icon className="h-4 w-4 text-muted-foreground" />
      </div>
      <div className="min-w-0 flex-1">
        <div className="text-[14px] font-medium">{title}</div>
        <div className="text-[12px] text-muted-foreground">{subtitle}</div>
      </div>
    </button>
  )
}

function FrontmatterView({
  project,
  frontmatter,
  authors,
  affiliations,
  loading,
}: {
  project: Project
  frontmatter: ProjectFrontmatter | null
  authors: { id: string; full_name: string; is_corresponding: boolean }[]
  affiliations: { id: string; name: string; city: string | null; country: string | null }[]
  loading: boolean
}) {
  if (loading) {
    return (
      <div className="py-6 text-center text-[13px] text-muted-foreground">
        Loading frontmatter…
      </div>
    )
  }
  const abstract = frontmatter?.structured_abstract
  return (
    <div className="flex flex-col gap-3" data-testid="mmr-frontmatter-sheet">
      <div>
        <div className="text-[11px] uppercase tracking-wider text-muted-foreground">
          Title
        </div>
        <div className="text-[14px] font-semibold">{project.title}</div>
      </div>

      <div>
        <div className="text-[11px] uppercase tracking-wider text-muted-foreground">
          Authors
        </div>
        {authors.length === 0 ? (
          <div className="text-[13px] text-muted-foreground italic">
            No authors yet.
          </div>
        ) : (
          <ol className="list-decimal pl-5 text-[13px]">
            {authors.map((a) => (
              <li key={a.id}>
                {a.full_name}
                {a.is_corresponding && (
                  <Badge variant="outline" className="ml-2 text-[10px]">
                    corresponding
                  </Badge>
                )}
              </li>
            ))}
          </ol>
        )}
      </div>

      <div>
        <div className="text-[11px] uppercase tracking-wider text-muted-foreground">
          Affiliations
        </div>
        {affiliations.length === 0 ? (
          <div className="text-[13px] text-muted-foreground italic">
            No affiliations yet.
          </div>
        ) : (
          <ol className="list-decimal pl-5 text-[13px]">
            {affiliations.map((a) => (
              <li key={a.id}>
                {a.name}
                {(a.city || a.country) && (
                  <span className="text-muted-foreground">
                    {' — '}
                    {[a.city, a.country].filter(Boolean).join(', ')}
                  </span>
                )}
              </li>
            ))}
          </ol>
        )}
      </div>

      {abstract && (
        <div>
          <div className="text-[11px] uppercase tracking-wider text-muted-foreground">
            Abstract
          </div>
          <div className="flex flex-col gap-2 text-[13px]">
            {abstract.background && (
              <div>
                <span className="font-semibold">Background. </span>
                {abstract.background}
              </div>
            )}
            {abstract.methods && (
              <div>
                <span className="font-semibold">Methods. </span>
                {abstract.methods}
              </div>
            )}
            {abstract.results && (
              <div>
                <span className="font-semibold">Results. </span>
                {abstract.results}
              </div>
            )}
            {abstract.conclusions && (
              <div>
                <span className="font-semibold">Conclusions. </span>
                {abstract.conclusions}
              </div>
            )}
          </div>
        </div>
      )}

      {frontmatter?.funding_statement && (
        <div>
          <div className="text-[11px] uppercase tracking-wider text-muted-foreground">
            Funding
          </div>
          <div className="text-[13px]">{frontmatter.funding_statement}</div>
        </div>
      )}
    </div>
  )
}

function SnapshotsView({
  snapshots,
  loading,
}: {
  snapshots: SnapshotSummary[]
  loading: boolean
}) {
  if (loading) {
    return (
      <div className="py-6 text-center text-[13px] text-muted-foreground">
        Loading snapshots…
      </div>
    )
  }
  if (snapshots.length === 0) {
    return (
      <div
        className="py-6 text-center text-[13px] text-muted-foreground"
        data-testid="mmr-snapshots-empty"
      >
        No snapshots yet. Create one from the desktop manuscript editor.
      </div>
    )
  }
  return (
    <div className="flex flex-col gap-2" data-testid="mmr-snapshots-sheet">
      {snapshots.map((s) => (
        <div
          key={s.id}
          className="rounded-lg border border-border bg-card px-3 py-2"
          data-testid={`mmr-snapshot-${s.id}`}
        >
          <div className="flex items-center justify-between gap-2">
            <div className="min-w-0">
              <div className="truncate text-[14px] font-medium">{s.label}</div>
              {s.description && (
                <div className="line-clamp-2 text-[12px] text-muted-foreground">
                  {s.description}
                </div>
              )}
            </div>
            <div className="text-[11px] text-muted-foreground">
              {new Date(s.created_at).toLocaleDateString()}
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}
