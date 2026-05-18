import {
  DndContext,
  type DragEndEvent,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors,
} from '@dnd-kit/core'
import {
  SortableContext,
  arrayMove,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'

import { frontmatterApi, type AffiliationRead } from '@/lib/api'

export function AffiliationsEditor({ projectId }: { projectId: string }) {
  const qc = useQueryClient()
  const affsQ = useQuery({
    queryKey: ['frontmatter', projectId, 'affiliations'],
    queryFn: () => frontmatterApi.affiliations.list(projectId),
  })
  const reorderMut = useMutation({
    mutationFn: (orderedIds: string[]) =>
      frontmatterApi.affiliations.reorder(projectId, orderedIds),
    onSuccess: (rows) =>
      qc.setQueryData(['frontmatter', projectId, 'affiliations'], rows),
  })
  const createMut = useMutation({
    mutationFn: (name: string) =>
      frontmatterApi.affiliations.create(projectId, { name }),
    onSuccess: () =>
      qc.invalidateQueries({
        queryKey: ['frontmatter', projectId, 'affiliations'],
      }),
  })

  const [newName, setNewName] = useState('')

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 4 } }),
  )

  if (affsQ.isLoading) {
    return (
      <div className="text-sm text-muted-foreground">Loading affiliations…</div>
    )
  }
  const affiliations = affsQ.data ?? []

  function onDragEnd(ev: DragEndEvent) {
    const { active, over } = ev
    if (!over || active.id === over.id) return
    const oldIdx = affiliations.findIndex((a) => a.id === active.id)
    const newIdx = affiliations.findIndex((a) => a.id === over.id)
    if (oldIdx === -1 || newIdx === -1) return
    const reordered = arrayMove(affiliations, oldIdx, newIdx)
    reorderMut.mutate(reordered.map((a) => a.id))
  }

  return (
    <div className="space-y-3">
      <div className="flex items-end gap-2">
        <div className="flex-1">
          <label className="block text-xs font-medium text-muted-foreground mb-1">
            Add affiliation
          </label>
          <input
            type="text"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            placeholder="Institution name"
            data-testid="aff-new-name"
            className="w-full rounded border border-border bg-background px-2 py-1.5 text-sm"
          />
        </div>
        <button
          onClick={() => {
            if (newName.trim()) {
              createMut.mutate(newName.trim())
              setNewName('')
            }
          }}
          data-testid="aff-add-btn"
          className="rounded bg-foreground px-3 py-1.5 text-sm text-background"
        >
          Add
        </button>
      </div>
      {affiliations.length === 0 ? (
        <div className="text-sm text-muted-foreground">No affiliations yet.</div>
      ) : (
        <DndContext
          sensors={sensors}
          collisionDetection={closestCenter}
          onDragEnd={onDragEnd}
        >
          <SortableContext
            items={affiliations.map((a) => a.id)}
            strategy={verticalListSortingStrategy}
          >
            <div className="space-y-2">
              {affiliations.map((aff) => (
                <AffiliationRow
                  key={aff.id}
                  aff={aff}
                  projectId={projectId}
                />
              ))}
            </div>
          </SortableContext>
        </DndContext>
      )}
    </div>
  )
}

function AffiliationRow({
  aff,
  projectId,
}: {
  aff: AffiliationRead
  projectId: string
}) {
  const qc = useQueryClient()
  const drag = useSortable({ id: aff.id })
  const style = {
    transform: CSS.Transform.toString(drag.transform),
    transition: drag.transition,
    opacity: drag.isDragging ? 0.6 : 1,
  }
  const updateMut = useMutation({
    mutationFn: (patch: Partial<AffiliationRead>) =>
      frontmatterApi.affiliations.update(aff.id, {
        name: patch.name,
        address: patch.address as string | null | undefined,
        city: patch.city as string | null | undefined,
        country: patch.country as string | null | undefined,
      }),
    onSuccess: () =>
      qc.invalidateQueries({
        queryKey: ['frontmatter', projectId, 'affiliations'],
      }),
  })
  const deleteMut = useMutation({
    mutationFn: () => frontmatterApi.affiliations.delete(aff.id),
    onSuccess: () =>
      qc.invalidateQueries({
        queryKey: ['frontmatter', projectId, 'affiliations'],
      }),
  })

  return (
    <div
      ref={drag.setNodeRef}
      style={style}
      data-testid={`aff-row-${aff.id}`}
      className="rounded border border-border bg-background p-3"
    >
      <div className="flex items-start gap-3">
        <button
          type="button"
          {...drag.attributes}
          {...drag.listeners}
          className="cursor-grab pt-1 text-muted-foreground hover:text-foreground"
          aria-label="Drag to reorder"
        >
          ⋮⋮
        </button>
        <div className="flex-1 space-y-2">
          <input
            value={aff.name}
            onChange={(e) => updateMut.mutate({ name: e.target.value })}
            data-testid={`aff-name-${aff.id}`}
            className="w-full rounded border border-border px-2 py-1.5 text-sm font-medium"
          />
          <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
            <input
              value={aff.address ?? ''}
              onChange={(e) =>
                updateMut.mutate({ address: e.target.value || null })
              }
              placeholder="Address"
              className="rounded border border-border px-2 py-1.5 text-sm"
            />
            <input
              value={aff.city ?? ''}
              onChange={(e) =>
                updateMut.mutate({ city: e.target.value || null })
              }
              placeholder="City"
              className="rounded border border-border px-2 py-1.5 text-sm"
            />
            <input
              value={aff.country ?? ''}
              onChange={(e) =>
                updateMut.mutate({ country: e.target.value || null })
              }
              placeholder="Country"
              className="rounded border border-border px-2 py-1.5 text-sm"
            />
          </div>
        </div>
        <button
          onClick={() => deleteMut.mutate()}
          data-testid={`aff-delete-${aff.id}`}
          className="text-xs text-rose-600 hover:underline"
        >
          Delete
        </button>
      </div>
    </div>
  )
}
