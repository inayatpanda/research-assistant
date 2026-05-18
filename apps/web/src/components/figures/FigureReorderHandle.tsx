/**
 * Reorder handle stub. The first iteration of FiguresPanel uses up/down
 * buttons for accessibility + screenshot stability; this component is the
 * future home of a `@dnd-kit/sortable` drag handle.
 */
export function FigureReorderHandle() {
  return (
    <span aria-hidden="true" className="cursor-grab text-muted-foreground">
      ⋮⋮
    </span>
  )
}
