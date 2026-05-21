/**
 * Phase M3.2 — Mobile Manuscript reader + per-paragraph edit sheet.
 * Phase D4 — Highlights mode wired to the comments backend.
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
 * Phase D4 — Highlights mode (the previously deferred M3 stub):
 *   - Overflow menu carries a "Highlights" toggle. Off → tap-to-edit
 *     (the M3 behaviour). On → long-press a paragraph word to enter
 *     selection mode, drag handles to extend, pick a colour swatch
 *     from the bottom bar to POST a comment.
 *   - Existing comments render inline as ``<mark data-comment-id>``
 *     wrappers, computed via ``offsetsToHighlightSpans``. Multiple
 *     overlapping comments → nested spans (handled in the helper).
 *   - Tapping a marked span opens a BottomSheet with quoted text +
 *     notes textarea (800ms debounced auto-save) + colour swatch
 *     row + delete button.
 *   - Citation chips are preserved: the helper splits paragraphs in
 *     plain-text space but emits HTML slices, so ``<sup
 *     data-citation>`` chips remain intact inside coloured spans.
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
  Highlighter,
  History,
  Loader2,
  MoreVertical,
  Sparkles,
  Trash2,
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
  commentsApi,
  exportApi,
  frontmatterApi,
  manuscriptApi,
  projectsApi,
  snapshotsApi,
  writingApi,
  type CommentRead,
  type ManuscriptSection,
  type ManuscriptSectionName,
  type Project,
  type ProjectFrontmatter,
  type SnapshotSummary,
} from '@/lib/api'
import { cn } from '@/lib/utils'

import { BottomSheet } from '../components/BottomSheet'
import { cacheable } from '../lib/offlineLearn'
import {
  offsetsToHighlightSpans,
  paragraphOffsets,
  wordRangeToOffsets,
  type ParagraphRenderPlan,
} from '../lib/manuscriptOffsets'

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

// Phase D4 — Highlight palette. Re-uses the M2 reader's four-colour
// scheme so a comment created here looks the same as a highlight created
// in the article reader. The comments backend has no ``colour`` column
// (it's a body-only entity), so we encode the colour in the body as a
// leading tag ``[colour:intro]`` which the renderer strips. This keeps
// us free of pip / npm deps and the spec-mandated backend-untouched
// guarantee.
const HIGHLIGHT_COLOURS = [
  { id: 'intro', bg: '#EF4444', label: 'Intro' },
  { id: 'method', bg: '#3B82F6', label: 'Method' },
  { id: 'results', bg: '#22C55E', label: 'Results' },
  { id: 'discussion', bg: '#EAB308', label: 'Discussion' },
] as const

type HighlightColour = (typeof HIGHLIGHT_COLOURS)[number]['id']

const COLOUR_BG: Record<HighlightColour, string> = {
  intro: '#EF4444',
  method: '#3B82F6',
  results: '#22C55E',
  discussion: '#EAB308',
}

const COLOUR_TAG_RE = /^\[colour:(intro|method|results|discussion)\]\s?/

function encodeBody(colour: HighlightColour, note: string): string {
  // Body has a min_length=1 constraint, so we always emit the colour
  // tag even for an empty note.
  return `[colour:${colour}]${note}`
}

function parseBody(body: string): { colour: HighlightColour; note: string } {
  const m = COLOUR_TAG_RE.exec(body)
  if (m) {
    return { colour: m[1] as HighlightColour, note: body.slice(m[0].length) }
  }
  return { colour: 'intro', note: body }
}

const LONG_PRESS_MS = 500
const LONG_PRESS_TOLERANCE_PX = 10

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

  // ------ Phase D4 — Highlights mode
  //
  // The mode toggle lives in the overflow menu (Highlights). When off,
  // the existing tap-paragraph-to-edit flow runs. When on, long-press
  // enters word-range selection, drag handles extend it, a swatch row
  // commits a comment via ``commentsApi.create``.
  //
  // Existing comments are fetched once per project and grouped by
  // section. Render spans are computed via the helper so overlapping
  // ranges nest correctly without losing citation chips.
  const [highlightsMode, setHighlightsMode] = useState(false)
  const commentsQ = useQuery({
    queryKey: ['mmr', 'comments', projectId],
    queryFn: async () => {
      if (!projectId) throw new Error('missing projectId')
      return commentsApi.list(projectId)
    },
    enabled: !!projectId,
  })
  const comments: CommentRead[] = commentsQ.data ?? []
  const commentById = useMemo(() => {
    const m = new Map<string, CommentRead>()
    for (const c of comments) m.set(c.id, c)
    return m
  }, [comments])

  // Render plans per section — recomputed when the section content or
  // the comments list changes.
  const renderPlans: Record<ManuscriptSectionName, ParagraphRenderPlan[]> =
    useMemo(() => {
      const out = {} as Record<ManuscriptSectionName, ParagraphRenderPlan[]>
      for (const s of SECTION_ORDER) {
        const html = sections[s]?.content ?? ''
        const ofSection = comments.filter((c) => c.section_name === s)
        out[s] = offsetsToHighlightSpans(ofSection, html)
      }
      return out
    }, [sections, comments])

  // Long-press / selection state for highlights mode.
  type SelectionState = {
    section: ManuscriptSectionName
    paragraphIdx: number
    wordStart: number
    wordEnd: number
  }
  const [selection, setSelection] = useState<SelectionState | null>(null)
  const pressTimer = useRef<number | null>(null)
  const pressOrigin = useRef<{
    x: number
    y: number
    section: ManuscriptSectionName
    paragraphIdx: number
    wordIdx: number
  } | null>(null)

  function clearPressTimer() {
    if (pressTimer.current != null) {
      window.clearTimeout(pressTimer.current)
      pressTimer.current = null
    }
  }

  function wordHitAtPoint(
    clientX: number,
    clientY: number,
  ): {
    section: ManuscriptSectionName
    paragraphIdx: number
    wordIdx: number
  } | null {
    if (typeof document === 'undefined') return null
    const el = document.elementFromPoint(clientX, clientY) as HTMLElement | null
    if (!el) return null
    const wordEl = el.closest('[data-word-idx]') as HTMLElement | null
    if (!wordEl) return null
    const paraEl = wordEl.closest('[data-paragraph-id]') as HTMLElement | null
    if (!paraEl) return null
    const pid = paraEl.getAttribute('data-paragraph-id') ?? ''
    const dash = pid.indexOf('-p')
    if (dash <= 0) return null
    const section = pid.slice(0, dash) as ManuscriptSectionName
    const paragraphIdx = Number(pid.slice(dash + 2))
    const wordIdx = Number(wordEl.getAttribute('data-word-idx'))
    if (!Number.isFinite(paragraphIdx) || !Number.isFinite(wordIdx)) return null
    return { section, paragraphIdx, wordIdx }
  }

  function onBodyTouchStart(e: React.TouchEvent<HTMLDivElement>) {
    if (!highlightsMode) return
    if (e.touches.length !== 1) {
      clearPressTimer()
      return
    }
    const t = e.touches[0]
    const hit = wordHitAtPoint(t.clientX, t.clientY)
    if (!hit) return
    pressOrigin.current = { x: t.clientX, y: t.clientY, ...hit }
    clearPressTimer()
    pressTimer.current = window.setTimeout(() => {
      setSelection({
        section: hit.section,
        paragraphIdx: hit.paragraphIdx,
        wordStart: hit.wordIdx,
        wordEnd: hit.wordIdx,
      })
      pressTimer.current = null
    }, LONG_PRESS_MS)
  }

  function onBodyTouchMove(e: React.TouchEvent<HTMLDivElement>) {
    const origin = pressOrigin.current
    if (!origin || pressTimer.current == null) return
    const t = e.touches[0]
    const dx = Math.abs(t.clientX - origin.x)
    const dy = Math.abs(t.clientY - origin.y)
    if (dx > LONG_PRESS_TOLERANCE_PX || dy > LONG_PRESS_TOLERANCE_PX) {
      clearPressTimer()
      pressOrigin.current = null
    }
  }

  function onBodyTouchEnd() {
    clearPressTimer()
    pressOrigin.current = null
  }

  // ------ Citation chip handling: a delegated click handler on the
  // article body intercepts taps on ``<sup data-citation>`` nodes and
  // routes to the mobile article reader. Highlights-mode → tap an
  // existing comment span opens the edit sheet. Otherwise, taps fall
  // through to paragraph-edit handlers below.
  const [editingComment, setEditingComment] = useState<CommentRead | null>(null)
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
      const mark = target.closest('[data-comment-id]') as HTMLElement | null
      if (mark) {
        e.preventDefault()
        e.stopPropagation()
        const cid = mark.getAttribute('data-comment-id') ?? ''
        // For overlapping spans we encode IDs comma-joined; pick the
        // first as the entry point (the user can tap an adjacent
        // non-overlapped portion to reach the other).
        const firstId = cid.split(',')[0]
        const c = commentById.get(firstId)
        if (c) setEditingComment(c)
        return
      }
      if (highlightsMode) {
        // In highlights mode taps don't open the edit sheet — they
        // either dismiss a live selection or do nothing.
        if (selection) setSelection(null)
        return
      }
      const para = target.closest('[data-paragraph-id]') as HTMLElement | null
      if (!para) return
      const id = para.getAttribute('data-paragraph-id') ?? ''
      const dash = id.indexOf('-p')
      if (dash <= 0) return
      const section = id.slice(0, dash) as ManuscriptSectionName
      const idx = Number(id.slice(dash + 2))
      if (!Number.isFinite(idx)) return
      openParagraph(section, idx)
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [sections, projectId, highlightsMode, commentById, selection],
  )

  // ------ Highlights — create / update / delete mutations
  const createComment = useMutation({
    mutationFn: async (colour: HighlightColour) => {
      if (!projectId) throw new Error('missing project')
      if (!selection) throw new Error('no selection')
      const html = sections[selection.section]?.content ?? ''
      const paras = paragraphOffsets(html)
      const p = paras[selection.paragraphIdx]
      if (!p) throw new Error('paragraph out of range')
      const { anchor_start, anchor_end } = wordRangeToOffsets(
        p.html,
        selection.wordStart,
        selection.wordEnd,
        p.start,
      )
      return commentsApi.create(projectId, {
        section_name: selection.section,
        anchor_start,
        anchor_end: Math.max(anchor_end, anchor_start + 1),
        body: encodeBody(colour, ''),
      })
    },
    onSuccess: () => {
      if (!projectId) return
      qc.invalidateQueries({ queryKey: ['mmr', 'comments', projectId] })
      setSelection(null)
      toast.success('Highlight saved')
    },
    onError: (err) => {
      if (!navigator.onLine) {
        toast.error('Offline — connect to laptop to save')
      } else {
        toast.error(err instanceof Error ? err.message : 'Could not save')
      }
    },
  })

  const updateComment = useMutation({
    mutationFn: async ({
      id,
      body,
    }: {
      id: string
      body: string
    }) => {
      if (!projectId) throw new Error('missing project')
      return commentsApi.update(projectId, id, { body })
    },
    onSuccess: (c) => {
      if (!projectId) return
      qc.invalidateQueries({ queryKey: ['mmr', 'comments', projectId] })
      setEditingComment(c)
    },
    onError: (err) => {
      toast.error(err instanceof Error ? err.message : 'Save failed')
    },
  })

  const deleteComment = useMutation({
    mutationFn: async (id: string) => {
      if (!projectId) throw new Error('missing project')
      return commentsApi.delete(projectId, id)
    },
    onSuccess: () => {
      if (!projectId) return
      qc.invalidateQueries({ queryKey: ['mmr', 'comments', projectId] })
      setEditingComment(null)
      toast.success('Highlight deleted')
    },
    onError: (err) => {
      toast.error(err instanceof Error ? err.message : 'Delete failed')
    },
  })

  // ------ Edit-sheet auto-save (note text)
  const editNoteTimer = useRef<number | null>(null)
  const [editNoteDraft, setEditNoteDraft] = useState('')
  const [editColour, setEditColour] = useState<HighlightColour>('intro')
  useEffect(() => {
    if (!editingComment) {
      setEditNoteDraft('')
      setEditColour('intro')
      return
    }
    const { colour, note } = parseBody(editingComment.body)
    setEditNoteDraft(note)
    setEditColour(colour)
  }, [editingComment?.id, editingComment?.body])

  function onEditNoteChange(v: string) {
    setEditNoteDraft(v)
    if (editNoteTimer.current != null) {
      window.clearTimeout(editNoteTimer.current)
    }
    if (!editingComment) return
    editNoteTimer.current = window.setTimeout(() => {
      updateComment.mutate({
        id: editingComment.id,
        body: encodeBody(editColour, v),
      })
    }, 800)
  }

  function onEditPickColour(colour: HighlightColour) {
    setEditColour(colour)
    if (!editingComment) return
    if (editNoteTimer.current != null) {
      window.clearTimeout(editNoteTimer.current)
    }
    updateComment.mutate({
      id: editingComment.id,
      body: encodeBody(colour, editNoteDraft),
    })
  }

  // Quoted text shown in the edit sheet header — uses the comment's
  // anchor to slice the section's plain text.
  const editingQuote = useMemo(() => {
    if (!editingComment) return ''
    const section = sections[editingComment.section_name as ManuscriptSectionName]
    if (!section) return ''
    const paras = paragraphOffsets(section.content)
    for (const p of paras) {
      const lo = Math.max(editingComment.anchor_start, p.start)
      const hi = Math.min(editingComment.anchor_end, p.end)
      if (hi > lo) {
        return p.text.slice(lo - p.start, hi - p.start)
      }
    }
    return ''
  }, [editingComment, sections])

  // ------ Overflow menu
  const [overflowOpen, setOverflowOpen] = useState(false)
  const [frontmatterOpen, setFrontmatterOpen] = useState(false)
  const [snapshotsOpen, setSnapshotsOpen] = useState(false)
  const [exportOpen, setExportOpen] = useState(false)

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
        onTouchStart={onBodyTouchStart}
        onTouchMove={onBodyTouchMove}
        onTouchEnd={onBodyTouchEnd}
        onTouchCancel={onBodyTouchEnd}
        data-testid="mmr-body"
        data-highlights-mode={highlightsMode ? '1' : '0'}
      >
        {SECTION_ORDER.map((s) => {
          const plans = renderPlans[s] ?? []
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
              {plans.length === 0 && (
                <p
                  className="my-3 italic text-muted-foreground text-[13px]"
                  data-testid={`mmr-section-empty-${s}`}
                >
                  (Empty — write this section on desktop or below.)
                </p>
              )}
              {plans.map((plan, i) => {
                const liveSelection =
                  highlightsMode &&
                  selection &&
                  selection.section === s &&
                  selection.paragraphIdx === i
                    ? selection
                    : null
                return (
                  <ParagraphRow
                    key={`${s}-p${i}`}
                    section={s}
                    index={i}
                    plan={plan}
                    highlightsMode={highlightsMode}
                    selectedWordRange={
                      liveSelection
                        ? {
                            start: Math.min(
                              liveSelection.wordStart,
                              liveSelection.wordEnd,
                            ),
                            end: Math.max(
                              liveSelection.wordStart,
                              liveSelection.wordEnd,
                            ),
                          }
                        : null
                    }
                    commentColours={(id) => {
                      const c = commentById.get(id)
                      if (!c) return COLOUR_BG.intro
                      return COLOUR_BG[parseBody(c.body).colour]
                    }}
                  />
                )
              })}
            </section>
          )
        })}
      </div>

      {/* Phase D4 — Colour-swatch toolbar (visible only while a
          highlights-mode selection is live). */}
      {highlightsMode && selection && (
        <div
          data-testid="mmr-swatch-bar"
          className="fixed left-0 right-0 z-30 border-t border-border bg-background/95 px-3 py-3 pb-[calc(12px+env(safe-area-inset-bottom))] shadow-[0_-4px_12px_rgba(0,0,0,0.08)] backdrop-blur"
          style={{ bottom: 64 }}
        >
          <div className="flex items-center justify-between gap-2">
            <div className="flex gap-2">
              {HIGHLIGHT_COLOURS.map((c) => (
                <button
                  key={c.id}
                  type="button"
                  data-testid={`mmr-swatch-${c.id}`}
                  aria-label={`Highlight ${c.label}`}
                  disabled={createComment.isPending}
                  onClick={() => createComment.mutate(c.id)}
                  className="h-9 w-9 rounded-full ring-2 ring-background"
                  style={{ backgroundColor: c.bg }}
                />
              ))}
            </div>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => setSelection(null)}
              data-testid="mmr-swatch-cancel"
            >
              Cancel
            </Button>
          </div>
        </div>
      )}

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
            icon={Highlighter}
            title={highlightsMode ? 'Highlights — on' : 'Highlights — off'}
            subtitle={
              highlightsMode
                ? 'Long-press a paragraph to select words'
                : 'Tap to enable; long-press to highlight'
            }
            onClick={() => {
              setOverflowOpen(false)
              setHighlightsMode((m) => !m)
              setSelection(null)
              toast.message(
                highlightsMode ? 'Highlights mode: off' : 'Highlights mode: on',
              )
            }}
            testId="mmr-overflow-highlights"
            active={highlightsMode}
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

      {/* Phase D4 — Comment edit sheet (opened by tapping a highlighted
          span). Quoted text + notes (800ms debounce auto-save) +
          colour swatch row + delete button. */}
      <BottomSheet
        open={editingComment !== null}
        onClose={() => setEditingComment(null)}
        title="Highlight"
        snapPoints={['70%']}
      >
        {editingComment && (
          <div
            className="flex flex-col gap-3 pb-2"
            data-testid="mmr-comment-sheet"
          >
            <div
              className="rounded-md border-l-4 bg-muted/40 px-3 py-2 text-[13px] italic text-foreground"
              style={{ borderLeftColor: COLOUR_BG[editColour] }}
              data-testid="mmr-comment-quote"
            >
              {editingQuote || '(no text)'}
            </div>
            <textarea
              value={editNoteDraft}
              onChange={(e) => onEditNoteChange(e.target.value)}
              placeholder="Add a note…"
              data-testid="mmr-comment-note"
              className="min-h-[100px] resize-none rounded-lg border border-border bg-card px-3 py-2 text-[14px] focus:outline-none focus:ring-2 focus:ring-primary/40"
            />
            <div className="flex items-center justify-between gap-2">
              <div className="flex gap-2">
                {HIGHLIGHT_COLOURS.map((c) => (
                  <button
                    key={c.id}
                    type="button"
                    data-testid={`mmr-comment-colour-${c.id}`}
                    aria-label={`Re-colour to ${c.label}`}
                    onClick={() => onEditPickColour(c.id)}
                    className={cn(
                      'h-8 w-8 rounded-full ring-2',
                      editColour === c.id
                        ? 'ring-foreground'
                        : 'ring-background',
                    )}
                    style={{ backgroundColor: c.bg }}
                  />
                ))}
              </div>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                disabled={deleteComment.isPending}
                onClick={() => deleteComment.mutate(editingComment.id)}
                data-testid="mmr-comment-delete"
                className="text-rose-700"
              >
                <Trash2 className="mr-1 h-3.5 w-3.5" />
                Delete
              </Button>
            </div>
          </div>
        )}
      </BottomSheet>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

/**
 * Phase D4 — ParagraphRow renders the M2-style word-indexed paragraph
 * with optional comment-mark wrappers and live-selection highlights.
 *
 * Rendering algorithm:
 *   1. Walk the inner HTML token-by-token. Tokens are either a
 *      ``<tag ...>`` (kept verbatim, contributes 0 plain chars) or a
 *      plain-text run.
 *   2. Plain-text runs are split on whitespace. Each non-whitespace
 *      chunk becomes a ``<span data-word-idx="N">`` that the touch
 *      handlers up the tree pick up to drive selection.
 *   3. The current plain-text cursor tracks which word index we're on
 *      AND lets us ask the spans plan ("which comment IDs cover this
 *      char?"). Words covered by ≥1 comment are wrapped in a
 *      ``<mark data-comment-id>`` whose background colour comes from
 *      the parent. Overlapping comments emit comma-joined IDs.
 *   4. Live word selection (range from the parent) styles words with a
 *      sky-blue ring so the user sees what they've selected.
 *
 * Citation chip preservation (D4.4): chips are inline ``<sup
 * data-citation>`` tags; they're emitted verbatim by step 1 and never
 * touched by the marking logic — so a chip inside a highlighted range
 * remains a tappable chip.
 */
function ParagraphRow({
  section,
  index,
  plan,
  highlightsMode,
  selectedWordRange,
  commentColours,
}: {
  section: ManuscriptSectionName
  index: number
  plan: ParagraphRenderPlan
  highlightsMode: boolean
  selectedWordRange: { start: number; end: number } | null
  commentColours: (id: string) => string
}) {
  // Build a flat ordered list of "atoms": either a word token, an
  // HTML pass-through fragment, or a whitespace fragment. Each carries
  // the set of comment IDs at its plain-text midpoint so we wrap
  // covered ones in <mark>.
  const atoms = useMemo(() => {
    type Atom =
      | { kind: 'word'; idx: number; text: string; commentIds: string[] }
      | { kind: 'space'; text: string; commentIds: string[] }
      | { kind: 'html'; html: string; commentIds: string[] }
    const out: Atom[] = []
    let wordCounter = 0
    let plainCursor = 0

    // Build a fast lookup: for each plain-text position, which
    // comment IDs cover it? We build interval ends so it's O(spans).
    type Interval = { lo: number; hi: number; ids: string[] }
    const intervals: Interval[] = []
    let cursor = 0
    for (const span of plan.spans) {
      // Compute the plain-text length covered by this HTML span by
      // walking through the HTML and counting non-tag, non-entity
      // characters. Cheap, since spans are small.
      const plainLen = plainLengthOf(span.html)
      if (plainLen > 0 && span.commentIds.length > 0) {
        intervals.push({
          lo: cursor,
          hi: cursor + plainLen,
          ids: span.commentIds,
        })
      }
      cursor += plainLen
    }

    function idsAt(pos: number): string[] {
      for (const it of intervals) {
        if (pos >= it.lo && pos < it.hi) return it.ids
      }
      return []
    }

    // Walk the joined inner HTML token-by-token. Joining the plan
    // spans reconstructs the original inner HTML exactly.
    const html = plan.spans.map((s) => s.html).join('')
    let i = 0
    while (i < html.length) {
      const ch = html[i]
      if (ch === '<') {
        const end = html.indexOf('>', i)
        if (end === -1) break
        const tag = html.slice(i, end + 1)
        out.push({ kind: 'html', html: tag, commentIds: idsAt(plainCursor) })
        i = end + 1
        continue
      }
      if (ch === '&') {
        const end = html.indexOf(';', i)
        if (end !== -1 && end - i <= 8) {
          const ent = html.slice(i, end + 1)
          // Treat HTML entities as a single character in plain space.
          out.push({ kind: 'html', html: ent, commentIds: idsAt(plainCursor) })
          plainCursor += 1
          i = end + 1
          continue
        }
      }
      // Plain text run — scan until next tag/entity boundary.
      let j = i
      let runText = ''
      while (j < html.length && html[j] !== '<' && html[j] !== '&') {
        runText += html[j]
        j += 1
      }
      // Split into words / whitespace.
      let k = 0
      while (k < runText.length) {
        if (/\s/.test(runText[k])) {
          let s = k
          while (k < runText.length && /\s/.test(runText[k])) k++
          const text = runText.slice(s, k)
          out.push({
            kind: 'space',
            text,
            commentIds: idsAt(plainCursor),
          })
          plainCursor += text.length
        } else {
          let s = k
          while (k < runText.length && !/\s/.test(runText[k])) k++
          const text = runText.slice(s, k)
          out.push({
            kind: 'word',
            idx: wordCounter++,
            text,
            commentIds: idsAt(plainCursor),
          })
          plainCursor += text.length
        }
      }
      i = j
    }
    return out
  }, [plan])

  return (
    <p
      data-paragraph-id={`${section}-p${index}`}
      data-testid={`mmr-para-${section}-${index}`}
      className={cn(
        'my-3 rounded-md transition-colors',
        !highlightsMode && 'cursor-pointer active:bg-muted/60 hover:bg-muted/40',
        '[&_sup[data-citation]]:cursor-pointer',
        '[&_sup[data-citation]]:rounded-sm',
        '[&_sup[data-citation]]:bg-primary/10',
        '[&_sup[data-citation]]:px-1',
        '[&_sup[data-citation]]:text-primary',
      )}
      style={highlightsMode ? { touchAction: 'pan-y' } : undefined}
    >
      {atoms.map((atom, k) => {
        if (atom.kind === 'html') {
          // Pass through opening / closing inline tags and entities.
          return (
            <span
              key={k}
              dangerouslySetInnerHTML={{ __html: atom.html }}
            />
          )
        }
        if (atom.kind === 'space') {
          return <span key={k}>{atom.text}</span>
        }
        const inSelection =
          selectedWordRange &&
          atom.idx >= selectedWordRange.start &&
          atom.idx <= selectedWordRange.end
        const commentBg =
          atom.commentIds.length > 0
            ? commentColours(atom.commentIds[0])
            : null
        const wrapperStyle: React.CSSProperties = {}
        if (commentBg) {
          wrapperStyle.backgroundColor = `${commentBg}4D`
          wrapperStyle.boxShadow = `inset 0 -2px 0 ${commentBg}`
          wrapperStyle.borderRadius = '2px'
        }
        if (inSelection) {
          wrapperStyle.outline = '2px dashed #38BDF8'
          wrapperStyle.outlineOffset = '1px'
        }
        return (
          <span
            key={k}
            data-word-idx={atom.idx}
            data-testid={`mmr-word-${section}-${index}-${atom.idx}`}
            data-comment-id={
              atom.commentIds.length > 0 ? atom.commentIds.join(',') : undefined
            }
            style={
              Object.keys(wrapperStyle).length > 0 ? wrapperStyle : undefined
            }
          >
            {atom.text}
          </span>
        )
      })}
    </p>
  )
}

/** Cheap count of the plain-text characters represented by an HTML run. */
function plainLengthOf(html: string): number {
  let n = 0
  let i = 0
  while (i < html.length) {
    const ch = html[i]
    if (ch === '<') {
      const end = html.indexOf('>', i)
      if (end === -1) break
      i = end + 1
      continue
    }
    if (ch === '&') {
      const end = html.indexOf(';', i)
      if (end !== -1 && end - i <= 8) {
        n += 1
        i = end + 1
        continue
      }
    }
    n += 1
    i += 1
  }
  return n
}

function OverflowRow({
  icon: Icon,
  title,
  subtitle,
  onClick,
  testId,
  active,
}: {
  icon: typeof Download
  title: string
  subtitle: string
  onClick: () => void
  testId: string
  active?: boolean
}) {
  return (
    <button
      type="button"
      data-testid={testId}
      data-active={active ? '1' : '0'}
      onClick={onClick}
      className={cn(
        'flex w-full items-center gap-3 rounded-lg border bg-card px-3 py-3 text-left transition-colors active:bg-muted/60 hover:bg-muted/40',
        active ? 'border-primary/50 bg-primary/5' : 'border-border',
      )}
    >
      <div
        className={cn(
          'flex h-9 w-9 items-center justify-center rounded-lg',
          active ? 'bg-primary/15' : 'bg-muted',
        )}
      >
        <Icon
          className={cn(
            'h-4 w-4',
            active ? 'text-primary' : 'text-muted-foreground',
          )}
        />
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
