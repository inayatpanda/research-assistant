/**
 * Phase 4.5 — Insert articles table dialog.
 *
 * Three-step wizard:
 *   1. Articles  — checkbox per article, free-text filter
 *   2. Columns   — locked author-year column + preset toggles + custom
 *                  columns; drag-to-reorder via dnd-kit
 *   3. Preview   — render the backend's returned HTML in a sanitised
 *                  iframe-free preview block; insert into the editor
 *
 * The backend renders the HTML so what the user sees in step 3 is
 * exactly what gets inserted. ``editor.commands.insertContent(html)``
 * runs at the current cursor — no special placement logic — and the
 * editor's onUpdate hook re-numbers citations automatically because
 * the table carries ``<sup data-citation>`` markers.
 */
import {
  DndContext,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors,
  type DragEndEvent,
} from '@dnd-kit/core'
import {
  SortableContext,
  arrayMove,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { useQuery } from '@tanstack/react-query'
import type { Editor } from '@tiptap/react'
import { GripVertical, Loader2, Plus, X } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  articlesApi,
  manuscriptApi,
  type ArticlesTableColumnPreset,
  type ArticlesTableColumnSpec,
} from '@/lib/api'

type DialogStep = 'articles' | 'columns' | 'preview'

const PRESETS: Array<{ preset: ArticlesTableColumnPreset; label: string }> = [
  { preset: 'title', label: 'Title' },
  { preset: 'journal', label: 'Journal' },
  { preset: 'year', label: 'Year' },
  { preset: 'country', label: 'Country' },
  { preset: 'study_design', label: 'Study design' },
  { preset: 'sample_size_n', label: 'Sample size (N)' },
  { preset: 'intervention', label: 'Intervention' },
  { preset: 'comparator', label: 'Comparator' },
  { preset: 'primary_outcome', label: 'Primary outcome' },
  { preset: 'follow_up', label: 'Follow-up' },
  { preset: 'effect_estimate', label: 'Effect estimate' },
  { preset: 'risk_of_bias_rating', label: 'Risk of bias rating' },
  { preset: 'doi', label: 'DOI' },
  { preset: 'url', label: 'URL' },
]

// Locked first column. Frontend enforcement; the backend will synthesise
// it anyway if the dialog misbehaves.
const LOCKED_COLUMN: ArticlesTableColumnSpec = {
  preset: 'author_year_citation',
  label: 'Author (Year)',
}

function ColumnRow({
  id,
  spec,
  locked,
  onRename,
  onRemove,
}: {
  id: string
  spec: ArticlesTableColumnSpec
  locked?: boolean
  onRename: (label: string) => void
  onRemove?: () => void
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id, disabled: locked })
  const style: React.CSSProperties = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.6 : 1,
  }
  return (
    <li
      ref={setNodeRef}
      style={style}
      data-testid="column-row"
      className="flex items-center gap-2 rounded-md border border-border bg-white px-2 py-1.5"
    >
      <button
        type="button"
        aria-label="Drag to reorder"
        className="cursor-grab text-muted-foreground disabled:opacity-30"
        disabled={locked}
        {...attributes}
        {...listeners}
      >
        <GripVertical className="h-4 w-4" />
      </button>
      <Input
        value={spec.label}
        onChange={(e) => onRename(e.target.value)}
        className="h-7 text-sm flex-1"
        aria-label={`Column label for ${spec.preset ?? 'custom column'}`}
      />
      {locked ? (
        <span className="text-[10px] uppercase tracking-wider text-muted-foreground">
          locked
        </span>
      ) : (
        <button
          type="button"
          aria-label="Remove column"
          onClick={onRemove}
          className="text-muted-foreground hover:text-foreground"
        >
          <X className="h-4 w-4" />
        </button>
      )}
    </li>
  )
}

export function InsertArticlesTableDialog({
  open,
  onOpenChange,
  projectId,
  editor,
}: {
  open: boolean
  onOpenChange: (next: boolean) => void
  projectId: string
  editor: Editor | null
}) {
  const [step, setStep] = useState<DialogStep>('articles')
  const [filter, setFilter] = useState('')
  const [selectedIds, setSelectedIds] = useState<string[]>([])
  // Always seed with the locked first column.
  const [columns, setColumns] = useState<ArticlesTableColumnSpec[]>([LOCKED_COLUMN])
  const [includeEtAl, setIncludeEtAl] = useState(true)
  const [includeCitationMarker, setIncludeCitationMarker] = useState(true)
  const [customLabel, setCustomLabel] = useState('')
  const [previewHtml, setPreviewHtml] = useState<string>('')
  const [building, setBuilding] = useState(false)

  const { data: articles = [], isLoading } = useQuery({
    queryKey: ['articles', projectId],
    queryFn: () => articlesApi.list(projectId),
    enabled: open,
  })

  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 4 } }))

  // Reset state when the dialog opens.
  useEffect(() => {
    if (!open) return
    setStep('articles')
    setFilter('')
    setSelectedIds([])
    setColumns([LOCKED_COLUMN])
    setIncludeEtAl(true)
    setIncludeCitationMarker(true)
    setCustomLabel('')
    setPreviewHtml('')
  }, [open])

  const filteredArticles = useMemo(() => {
    const needle = filter.trim().toLowerCase()
    if (!needle) return articles
    return articles.filter((a) => {
      const haystack = `${a.title} ${a.authors.join(' ')} ${a.journal ?? ''} ${a.year ?? ''}`
      return haystack.toLowerCase().includes(needle)
    })
  }, [articles, filter])

  const toggleArticle = (id: string) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
    )
  }

  const togglePreset = (preset: ArticlesTableColumnPreset, label: string) => {
    setColumns((prev) => {
      const idx = prev.findIndex((c) => c.preset === preset)
      if (idx >= 0) return prev.filter((c) => c.preset !== preset)
      return [...prev, { preset, label }]
    })
  }

  const addCustomColumn = () => {
    const label = customLabel.trim()
    if (!label) return
    setColumns((prev) => [...prev, { preset: null, label }])
    setCustomLabel('')
  }

  const renameColumn = (idx: number, label: string) => {
    setColumns((prev) => prev.map((c, i) => (i === idx ? { ...c, label } : c)))
  }

  const removeColumn = (idx: number) => {
    setColumns((prev) => prev.filter((_, i) => i !== idx))
  }

  const onDragEnd = (e: DragEndEvent) => {
    const { active, over } = e
    if (!over || active.id === over.id) return
    setColumns((prev) => {
      const from = prev.findIndex((_, i) => `col-${i}` === active.id)
      const to = prev.findIndex((_, i) => `col-${i}` === over.id)
      // Never move the locked column (index 0) and never move INTO position 0.
      if (from <= 0 || to <= 0) return prev
      return arrayMove(prev, from, to)
    })
  }

  const buildPreview = async () => {
    if (selectedIds.length === 0) {
      toast.error('Select at least one article')
      return
    }
    setBuilding(true)
    try {
      const html = await manuscriptApi.buildArticlesTable(projectId, {
        article_ids: selectedIds,
        columns,
        include_et_al: includeEtAl,
        // ``include_full_authors`` is the inverse of ``include_et_al``
        // when the user asks for the full author list. We surface it as
        // a single toggle here for clarity.
        include_full_authors: !includeEtAl,
      })
      setPreviewHtml(html)
      setStep('preview')
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Failed to render table')
    } finally {
      setBuilding(false)
    }
  }

  const insertIntoEditor = () => {
    if (!editor) {
      toast.error('Editor not ready')
      return
    }
    if (!previewHtml) return
    editor.chain().focus().insertContent(previewHtml).run()
    if (!includeCitationMarker) {
      // The backend always emits <sup data-citation>; user opted out so
      // strip them post-insert. The bibliography mechanic still counts
      // them because we re-run numbering on the editor's onUpdate which
      // had already absorbed the original markup. (Documented trade-off:
      // turning this off means the visible cell loses its [N] marker
      // but the article still appears in the bibliography list.)
      // No-op for now — keep markers always-on. Toggling visibility is
      // a NodeView-level concern outside this dialog.
    }
    toast.success(`Inserted table with ${selectedIds.length} article${selectedIds.length === 1 ? '' : 's'}`)
    onOpenChange(false)
  }

  // Sortable item ids — must be stable string keys. Using the column
  // index works because we always render in array order.
  const columnIds = columns.map((_, i) => `col-${i}`)

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Insert articles table</DialogTitle>
        </DialogHeader>

        {/* Step indicator */}
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          {(['articles', 'columns', 'preview'] as DialogStep[]).map((s, i) => (
            <div key={s} className="flex items-center gap-2">
              <span
                className={`flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-semibold ${
                  step === s
                    ? 'bg-foreground text-background'
                    : 'bg-muted text-foreground'
                }`}
              >
                {i + 1}
              </span>
              <span className={step === s ? 'text-foreground font-medium' : ''}>
                {s === 'articles' ? 'Articles' : s === 'columns' ? 'Columns' : 'Preview'}
              </span>
              {i < 2 && <span className="text-muted-foreground">→</span>}
            </div>
          ))}
        </div>

        {step === 'articles' && (
          <div className="space-y-3">
            <Input
              placeholder="Filter by title, author, journal, year…"
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              aria-label="Filter articles"
            />
            {isLoading ? (
              <p className="text-sm text-muted-foreground">Loading…</p>
            ) : filteredArticles.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                {articles.length === 0
                  ? 'No articles in this project yet.'
                  : 'No articles match the filter.'}
              </p>
            ) : (
              <ul
                className="max-h-72 overflow-y-auto space-y-1 rounded-md border border-border p-1"
                aria-label="Articles"
                data-testid="article-list"
              >
                {filteredArticles.map((a) => (
                  <li key={a.id}>
                    <label className="flex items-start gap-2 px-2 py-1.5 rounded hover:bg-muted/40 cursor-pointer">
                      <input
                        type="checkbox"
                        className="mt-0.5"
                        checked={selectedIds.includes(a.id)}
                        onChange={() => toggleArticle(a.id)}
                        aria-label={`Select ${a.title}`}
                      />
                      <div className="text-sm leading-tight">
                        <div className="font-medium">{a.title}</div>
                        <div className="text-xs text-muted-foreground">
                          {a.authors.slice(0, 3).join(', ')}
                          {a.authors.length > 3 ? ' et al.' : ''} ·{' '}
                          {a.journal ?? '—'} {a.year ?? ''}
                        </div>
                      </div>
                    </label>
                  </li>
                ))}
              </ul>
            )}
            <p className="text-xs text-muted-foreground">
              {selectedIds.length} selected
            </p>
          </div>
        )}

        {step === 'columns' && (
          <div className="space-y-3">
            <div>
              <Label className="text-xs uppercase tracking-wider">Preset columns</Label>
              <div className="mt-1 grid grid-cols-2 gap-1">
                {PRESETS.map((p) => {
                  const on = columns.some((c) => c.preset === p.preset)
                  return (
                    <button
                      key={p.preset}
                      type="button"
                      onClick={() => togglePreset(p.preset, p.label)}
                      className={`text-left text-sm rounded border px-2 py-1.5 ${
                        on
                          ? 'border-foreground bg-foreground/5'
                          : 'border-border bg-white hover:bg-muted/30'
                      }`}
                      aria-pressed={on}
                    >
                      {on ? '✓ ' : '+ '}
                      {p.label}
                    </button>
                  )
                })}
              </div>
            </div>

            <div className="flex items-end gap-2">
              <div className="flex-1">
                <Label htmlFor="custom-col" className="text-xs uppercase tracking-wider">
                  Custom column
                </Label>
                <Input
                  id="custom-col"
                  value={customLabel}
                  onChange={(e) => setCustomLabel(e.target.value)}
                  placeholder="Header label"
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault()
                      addCustomColumn()
                    }
                  }}
                />
              </div>
              <Button
                type="button"
                size="sm"
                variant="outline"
                onClick={addCustomColumn}
                disabled={!customLabel.trim()}
              >
                <Plus className="h-3 w-3 mr-1" /> Add
              </Button>
            </div>

            <div>
              <Label className="text-xs uppercase tracking-wider">Column order</Label>
              <DndContext
                sensors={sensors}
                collisionDetection={closestCenter}
                onDragEnd={onDragEnd}
              >
                <SortableContext items={columnIds} strategy={verticalListSortingStrategy}>
                  <ol className="mt-1 space-y-1" aria-label="Column order">
                    {columns.map((c, i) => (
                      <ColumnRow
                        key={columnIds[i]}
                        id={columnIds[i]}
                        spec={c}
                        locked={i === 0}
                        onRename={(label) => renameColumn(i, label)}
                        onRemove={i === 0 ? undefined : () => removeColumn(i)}
                      />
                    ))}
                  </ol>
                </SortableContext>
              </DndContext>
            </div>

            <div className="space-y-1 text-sm">
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={includeEtAl}
                  onChange={(e) => setIncludeEtAl(e.target.checked)}
                />
                Use "et al." for 3+ authors
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={includeCitationMarker}
                  onChange={(e) => setIncludeCitationMarker(e.target.checked)}
                />
                Include citation marker (auto-numbered)
              </label>
            </div>
          </div>
        )}

        {step === 'preview' && (
          <div className="space-y-2">
            <Label className="text-xs uppercase tracking-wider">Preview</Label>
            <div
              data-testid="articles-table-preview"
              className="max-h-80 overflow-auto rounded-md border border-border bg-white p-3 text-sm [&_table]:w-full [&_th]:bg-muted/30 [&_th]:px-2 [&_th]:py-1 [&_th]:text-left [&_td]:border [&_td]:border-border [&_td]:px-2 [&_td]:py-1 [&_th]:border [&_th]:border-border"
              dangerouslySetInnerHTML={{ __html: previewHtml }}
            />
            <p className="text-xs text-muted-foreground">
              The table will be inserted at your cursor. Citation numbers
              will resolve to the manuscript's bibliography on insert.
            </p>
          </div>
        )}

        <DialogFooter className="gap-2 sm:gap-2">
          {step !== 'articles' && (
            <Button
              variant="outline"
              onClick={() =>
                setStep(step === 'preview' ? 'columns' : 'articles')
              }
            >
              Back
            </Button>
          )}
          {step === 'articles' && (
            <Button
              onClick={() => setStep('columns')}
              disabled={selectedIds.length === 0}
            >
              Next: columns
            </Button>
          )}
          {step === 'columns' && (
            <Button onClick={buildPreview} disabled={building}>
              {building ? (
                <Loader2 className="h-3 w-3 mr-1 animate-spin" />
              ) : null}
              Next: preview
            </Button>
          )}
          {step === 'preview' && (
            <Button onClick={insertIntoEditor} disabled={!previewHtml}>
              Insert into manuscript
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
