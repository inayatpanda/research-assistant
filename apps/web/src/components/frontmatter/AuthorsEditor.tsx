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

import { LearnTooltip } from '@/components/learn/LearnTooltip'
import {
  frontmatterApi,
  type AffiliationRead,
  type AuthorRead,
} from '@/lib/api'

export function AuthorsEditor({ projectId }: { projectId: string }) {
  const qc = useQueryClient()
  const authorsQ = useQuery({
    queryKey: ['frontmatter', projectId, 'authors'],
    queryFn: () => frontmatterApi.authors.list(projectId),
  })
  const affsQ = useQuery({
    queryKey: ['frontmatter', projectId, 'affiliations'],
    queryFn: () => frontmatterApi.affiliations.list(projectId),
  })

  const reorderMut = useMutation({
    mutationFn: (orderedIds: string[]) =>
      frontmatterApi.authors.reorder(projectId, orderedIds),
    onSuccess: (rows) =>
      qc.setQueryData(['frontmatter', projectId, 'authors'], rows),
  })

  const createMut = useMutation({
    mutationFn: (full_name: string) =>
      frontmatterApi.authors.create(projectId, { full_name }),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ['frontmatter', projectId, 'authors'] }),
  })

  const [newName, setNewName] = useState('')

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 4 } }),
  )

  if (authorsQ.isLoading || affsQ.isLoading) {
    return <div className="text-sm text-muted-foreground">Loading authors…</div>
  }
  if (authorsQ.isError) {
    return <div className="text-sm text-rose-600">Failed to load authors</div>
  }
  const authors = authorsQ.data ?? []
  const affiliations = affsQ.data ?? []

  function onDragEnd(ev: DragEndEvent) {
    const { active, over } = ev
    if (!over || active.id === over.id) return
    const oldIdx = authors.findIndex((a) => a.id === active.id)
    const newIdx = authors.findIndex((a) => a.id === over.id)
    if (oldIdx === -1 || newIdx === -1) return
    const reordered = arrayMove(authors, oldIdx, newIdx)
    reorderMut.mutate(reordered.map((a) => a.id))
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
        <LearnTooltip
          concept="authorship-criteria"
          iconOnly
          description="The four ICMJE criteria — substantial contribution, drafting, approval, accountability — that every named author must meet."
        >
          ICMJE authorship criteria apply to everyone listed below.
        </LearnTooltip>
      </div>
      <div className="flex items-end gap-2">
        <div className="flex-1">
          <label className="block text-xs font-medium text-muted-foreground mb-1">
            Add author
          </label>
          <input
            type="text"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            placeholder="Full name"
            data-testid="author-new-name"
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
          data-testid="author-add-btn"
          className="rounded bg-foreground px-3 py-1.5 text-sm text-background"
        >
          Add
        </button>
      </div>
      {authors.length === 0 ? (
        <div className="text-sm text-muted-foreground">
          No authors yet. Add the first author above.
        </div>
      ) : (
        <DndContext
          sensors={sensors}
          collisionDetection={closestCenter}
          onDragEnd={onDragEnd}
        >
          <SortableContext
            items={authors.map((a) => a.id)}
            strategy={verticalListSortingStrategy}
          >
            <div className="space-y-2">
              {authors.map((a) => (
                <AuthorRow
                  key={a.id}
                  author={a}
                  affiliations={affiliations}
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

function AuthorRow({
  author,
  affiliations,
  projectId,
}: {
  author: AuthorRead
  affiliations: AffiliationRead[]
  projectId: string
}) {
  const qc = useQueryClient()
  const drag = useSortable({ id: author.id })
  const style = {
    transform: CSS.Transform.toString(drag.transform),
    transition: drag.transition,
    opacity: drag.isDragging ? 0.6 : 1,
  }
  const updateMut = useMutation({
    mutationFn: (patch: Partial<AuthorRead>) =>
      frontmatterApi.authors.update(author.id, {
        full_name: patch.full_name,
        given_name: patch.given_name,
        family_name: patch.family_name,
        orcid: patch.orcid as string | null | undefined,
        email: patch.email as string | null | undefined,
      }),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ['frontmatter', projectId, 'authors'] }),
  })
  const setCorrespondingMut = useMutation({
    mutationFn: () => frontmatterApi.authors.setCorresponding(author.id),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ['frontmatter', projectId, 'authors'] }),
  })
  const deleteMut = useMutation({
    mutationFn: () => frontmatterApi.authors.delete(author.id),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ['frontmatter', projectId, 'authors'] }),
  })
  const linkMut = useMutation({
    mutationFn: (affId: string) => frontmatterApi.link.add(author.id, affId),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ['frontmatter', projectId, 'authors'] }),
  })
  const unlinkMut = useMutation({
    mutationFn: (affId: string) => frontmatterApi.link.remove(author.id, affId),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ['frontmatter', projectId, 'authors'] }),
  })

  const [orcidDraft, setOrcidDraft] = useState(author.orcid ?? '')
  const [emailDraft, setEmailDraft] = useState(author.email ?? '')

  return (
    <div
      ref={drag.setNodeRef}
      style={style}
      data-testid={`author-row-${author.id}`}
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
          <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
            <input
              value={author.full_name}
              onChange={(e) =>
                updateMut.mutate({ full_name: e.target.value })
              }
              data-testid={`author-fullname-${author.id}`}
              className="rounded border border-border px-2 py-1.5 text-sm md:col-span-2"
            />
            <label className="flex items-center gap-2 text-xs">
              <input
                type="checkbox"
                checked={author.is_corresponding}
                onChange={() => setCorrespondingMut.mutate()}
                data-testid={`author-corresponding-${author.id}`}
              />
              Corresponding
            </label>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            <input
              type="text"
              placeholder="ORCID (0000-0000-0000-0000)"
              value={orcidDraft}
              onChange={(e) => setOrcidDraft(e.target.value)}
              onBlur={() =>
                updateMut.mutate({ orcid: orcidDraft || null })
              }
              data-testid={`author-orcid-${author.id}`}
              className="rounded border border-border px-2 py-1.5 text-sm font-mono"
            />
            <input
              type="email"
              placeholder="Email"
              value={emailDraft}
              onChange={(e) => setEmailDraft(e.target.value)}
              onBlur={() =>
                updateMut.mutate({ email: emailDraft || null })
              }
              data-testid={`author-email-${author.id}`}
              className="rounded border border-border px-2 py-1.5 text-sm"
            />
          </div>
          {affiliations.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {affiliations.map((aff) => {
                const linked = author.affiliation_ids.includes(aff.id)
                return (
                  <button
                    key={aff.id}
                    type="button"
                    onClick={() =>
                      linked
                        ? unlinkMut.mutate(aff.id)
                        : linkMut.mutate(aff.id)
                    }
                    data-testid={`author-aff-toggle-${author.id}-${aff.id}`}
                    className={`text-xs rounded px-2 py-1 border ${
                      linked
                        ? 'border-accent bg-accent/10 text-accent'
                        : 'border-border text-muted-foreground'
                    }`}
                  >
                    {aff.name}
                  </button>
                )
              })}
            </div>
          )}
        </div>
        <button
          onClick={() => deleteMut.mutate()}
          data-testid={`author-delete-${author.id}`}
          className="text-xs text-rose-600 hover:underline"
        >
          Delete
        </button>
      </div>
    </div>
  )
}
