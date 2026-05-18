import type { Figure } from '@/lib/api'

export function FigureCard({
  figure,
  onInsert,
  onDelete,
  onEdit,
  dragHandle,
}: {
  figure: Figure
  onInsert: () => void
  onDelete: () => void
  onEdit: () => void
  dragHandle?: React.ReactNode
}) {
  return (
    <div
      className="border border-border rounded bg-white p-2 space-y-2"
      data-testid={`figure-card-${figure.id}`}
    >
      <div className="flex items-start gap-2">
        {dragHandle}
        <div className="flex-1 min-w-0">
          <div className="text-[11px] font-medium text-muted-foreground">
            Figure {figure.figure_number}
          </div>
          {figure.file_url ? (
            <img
              src={figure.file_url}
              alt={figure.alt_text}
              className="mt-1 w-full max-h-32 object-contain border border-border rounded bg-zinc-50"
            />
          ) : (
            <div className="mt-1 h-24 bg-zinc-100 rounded" />
          )}
        </div>
      </div>
      {figure.caption && (
        <p className="text-xs text-foreground line-clamp-2">{figure.caption}</p>
      )}
      <div className="flex gap-1">
        <button
          onClick={onInsert}
          className="flex-1 text-xs px-2 py-1 rounded bg-zinc-900 text-white"
          aria-label={`Insert Figure ${figure.figure_number} into manuscript`}
        >
          Insert
        </button>
        <button
          onClick={onEdit}
          className="text-xs px-2 py-1 rounded border border-border"
          aria-label={`Edit Figure ${figure.figure_number} metadata`}
        >
          Edit
        </button>
        <button
          onClick={onDelete}
          className="text-xs px-2 py-1 rounded border border-border text-red-600"
          aria-label={`Delete Figure ${figure.figure_number}`}
        >
          Delete
        </button>
      </div>
    </div>
  )
}
