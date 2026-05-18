import { ImagePlus } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'
import type { Editor } from '@tiptap/react'

import {
  useDeleteFigure,
  useFigures,
  useReorderFigures,
  useUpdateFigure,
} from '@/hooks/useFigures'

import { FigureCard } from './FigureCard'
import { FigureUploadDialog } from './FigureUploadDialog'

export function FiguresPanel({
  projectId,
  editor,
}: {
  projectId: string
  editor?: Editor | null
}) {
  const { data: figures = [], isLoading } = useFigures(projectId)
  const remove = useDeleteFigure(projectId)
  const reorder = useReorderFigures(projectId)
  const update = useUpdateFigure(projectId)

  const [uploadOpen, setUploadOpen] = useState(false)
  const [editing, setEditing] = useState<string | null>(null)
  const [editCaption, setEditCaption] = useState('')
  const [editAlt, setEditAlt] = useState('')

  const onInsert = (figId: string, caption: string, altText: string) => {
    if (!editor) {
      toast.error('Editor not ready — switch to a section first')
      return
    }
    editor
      .chain()
      .focus()
      .insertContent({
        type: 'figure',
        attrs: { figureId: figId, caption, altText },
      })
      .run()
    toast.success('Figure inserted into manuscript')
  }

  const onDelete = async (figId: string) => {
    if (!confirm('Delete this figure? This cannot be undone.')) return
    try {
      await remove.mutateAsync(figId)
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Delete failed')
    }
  }

  const onMoveUp = async (idx: number) => {
    if (idx === 0) return
    const ids = figures.map((f) => f.id)
    ;[ids[idx - 1], ids[idx]] = [ids[idx], ids[idx - 1]]
    try {
      await reorder.mutateAsync(ids)
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Reorder failed')
    }
  }

  const onMoveDown = async (idx: number) => {
    if (idx >= figures.length - 1) return
    const ids = figures.map((f) => f.id)
    ;[ids[idx], ids[idx + 1]] = [ids[idx + 1], ids[idx]]
    try {
      await reorder.mutateAsync(ids)
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Reorder failed')
    }
  }

  const startEdit = (id: string) => {
    const fig = figures.find((f) => f.id === id)
    if (!fig) return
    setEditing(id)
    setEditCaption(fig.caption)
    setEditAlt(fig.alt_text)
  }

  const saveEdit = async () => {
    if (!editing) return
    try {
      await update.mutateAsync({ id: editing, body: { caption: editCaption, alt_text: editAlt } })
      setEditing(null)
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Save failed')
    }
  }

  return (
    <section
      aria-label="Figures panel"
      className="bg-white border border-border rounded-lg p-3 space-y-2"
    >
      <header className="flex items-center justify-between">
        <h3 className="text-sm font-semibold flex items-center gap-1">
          <ImagePlus className="w-4 h-4" /> Figures
        </h3>
        <button
          onClick={() => setUploadOpen(true)}
          className="text-xs px-2 py-1 rounded bg-zinc-900 text-white"
        >
          + Add figure
        </button>
      </header>

      {isLoading ? (
        <p className="text-xs text-muted-foreground">Loading…</p>
      ) : figures.length === 0 ? (
        <p className="text-xs text-muted-foreground">No figures yet. Upload to get started.</p>
      ) : (
        <ol className="space-y-2 list-none">
          {figures.map((f, idx) => (
            <li key={f.id} className="relative">
              <FigureCard
                figure={f}
                onInsert={() => onInsert(f.id, f.caption, f.alt_text)}
                onDelete={() => onDelete(f.id)}
                onEdit={() => startEdit(f.id)}
                dragHandle={
                  <div className="flex flex-col gap-0.5 pt-1" aria-label="Reorder figure">
                    <button
                      type="button"
                      aria-label="Move up"
                      disabled={idx === 0}
                      onClick={() => onMoveUp(idx)}
                      className="text-xs px-1 disabled:opacity-30"
                    >
                      ▲
                    </button>
                    <button
                      type="button"
                      aria-label="Move down"
                      disabled={idx === figures.length - 1}
                      onClick={() => onMoveDown(idx)}
                      className="text-xs px-1 disabled:opacity-30"
                    >
                      ▼
                    </button>
                  </div>
                }
              />
            </li>
          ))}
        </ol>
      )}

      {uploadOpen && (
        <FigureUploadDialog projectId={projectId} onClose={() => setUploadOpen(false)} />
      )}

      {editing && (
        <div
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
        >
          <div className="bg-white rounded-lg p-5 w-[460px] max-w-[90vw] space-y-3">
            <h3 className="text-base font-semibold">Edit figure metadata</h3>
            <label className="block">
              <span className="text-sm font-medium">Caption</span>
              <textarea
                value={editCaption}
                onChange={(e) => setEditCaption(e.target.value)}
                className="mt-1 block w-full rounded border border-border px-2 py-1 text-sm"
                rows={3}
              />
            </label>
            <label className="block">
              <span className="text-sm font-medium">Alt text</span>
              <input
                value={editAlt}
                maxLength={500}
                onChange={(e) => setEditAlt(e.target.value)}
                className="mt-1 block w-full rounded border border-border px-2 py-1 text-sm"
              />
            </label>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setEditing(null)}
                className="px-3 py-1.5 rounded border border-border text-sm"
              >
                Cancel
              </button>
              <button
                onClick={saveEdit}
                className="px-3 py-1.5 rounded bg-zinc-900 text-white text-sm"
              >
                Save
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  )
}
