/**
 * Phase 12 — Reviewer-response editor.
 *
 * Surface:
 *   - List of existing reviewer-response rows.
 *   - Per-row: reviewer label input, segmented {comment, response_html}
 *     table where the user edits each row, Save / Delete buttons.
 *   - "New reviewer" form at the bottom: label + raw_comments textarea +
 *     "Draft responses" button. POSTs the raw block, AI segments and
 *     drafts initial responses, the resulting row joins the list.
 */
import { useEffect, useState } from 'react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import type { CommentResponse, ReviewerResponseRead } from '@/lib/api'
import {
  useCreateReviewerResponse,
  useDeleteReviewerResponse,
  useReviewerResponses,
  useUpdateReviewerResponse,
} from '@/hooks/useReviewerResponses'

export function ReviewerResponseEditor({ projectId }: { projectId: string }) {
  const { data: rows = [], isLoading } = useReviewerResponses(projectId)
  const create = useCreateReviewerResponse(projectId)

  const [newLabel, setNewLabel] = useState('Reviewer 1')
  const [newRaw, setNewRaw] = useState('')

  async function handleCreate() {
    if (!newRaw.trim()) {
      toast.error('Paste the reviewer comments first')
      return
    }
    try {
      await create.mutateAsync({
        reviewer_label: newLabel.trim() || 'Reviewer',
        raw_comments: newRaw,
      })
      toast.success('Responses drafted')
      setNewRaw('')
    } catch (e) {
      const msg = (e as Error).message || ''
      if (/503/.test(msg)) toast.error('AI provider unavailable')
      else if (/429/.test(msg)) toast.error('AI rate limited')
      else toast.error(msg || 'Could not draft responses')
    }
  }

  return (
    <Card data-testid="reviewer-response-editor">
      <CardHeader>
        <CardTitle>Response to reviewers</CardTitle>
        <CardDescription>
          Paste each reviewer&apos;s full comments block. The AI segments
          into individual comments and drafts initial responses.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {isLoading ? (
          <div className="text-sm text-muted-foreground">Loading…</div>
        ) : (
          rows.map((row) => (
            <ReviewerResponseRow
              key={row.id}
              projectId={projectId}
              row={row}
            />
          ))
        )}

        <div className="rounded border border-dashed border-border bg-muted/40 p-3 space-y-2">
          <Label htmlFor="rr-new-label">Reviewer label</Label>
          <Input
            id="rr-new-label"
            value={newLabel}
            onChange={(e) => setNewLabel(e.target.value)}
            data-testid="rr-new-label"
          />
          <Label htmlFor="rr-new-raw">Raw comments block</Label>
          <Textarea
            id="rr-new-raw"
            rows={8}
            value={newRaw}
            placeholder={'1. Power calc.\n\n2. Fix typo.'}
            onChange={(e) => setNewRaw(e.target.value)}
            data-testid="rr-new-raw"
          />
          <div className="flex justify-end">
            <Button
              onClick={handleCreate}
              disabled={create.isPending}
              data-testid="rr-draft-button"
            >
              {create.isPending ? 'Drafting…' : 'Draft responses'}
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

function ReviewerResponseRow({
  projectId,
  row,
}: {
  projectId: string
  row: ReviewerResponseRead
}) {
  const update = useUpdateReviewerResponse(projectId)
  const remove = useDeleteReviewerResponse(projectId)
  const [label, setLabel] = useState(row.reviewer_label)
  const [comments, setComments] = useState<CommentResponse[]>(row.comments)

  useEffect(() => {
    setLabel(row.reviewer_label)
    setComments(row.comments)
  }, [row.id, row.reviewer_label, row.comments])

  function updateComment(idx: number, patch: Partial<CommentResponse>) {
    setComments((current) =>
      current.map((c, i) => (i === idx ? { ...c, ...patch } : c)),
    )
  }

  async function handleSave() {
    try {
      await update.mutateAsync({
        responseId: row.id,
        body: { reviewer_label: label, comments },
      })
      toast.success('Responses saved')
    } catch (e) {
      toast.error((e as Error).message || 'Could not save')
    }
  }

  async function handleDelete() {
    if (!window.confirm(`Delete "${row.reviewer_label}"?`)) return
    try {
      await remove.mutateAsync(row.id)
      toast.success('Deleted')
    } catch (e) {
      toast.error((e as Error).message || 'Could not delete')
    }
  }

  return (
    <div
      className="rounded border border-border bg-white p-3 space-y-3"
      data-testid={`rr-row-${row.id}`}
    >
      <div className="flex items-center gap-2">
        <Input
          value={label}
          onChange={(e) => setLabel(e.target.value)}
          className="max-w-xs"
          data-testid={`rr-label-${row.id}`}
        />
        <span className="text-xs text-muted-foreground">
          {comments.length} comment{comments.length === 1 ? '' : 's'}
        </span>
        <span className="flex-1" />
        <Button
          variant="ghost"
          size="sm"
          className="text-rose-600"
          onClick={handleDelete}
          data-testid={`rr-delete-${row.id}`}
        >
          Delete
        </Button>
        <Button
          onClick={handleSave}
          size="sm"
          disabled={update.isPending}
          data-testid={`rr-save-${row.id}`}
        >
          {update.isPending ? 'Saving…' : 'Save'}
        </Button>
      </div>
      <ul className="space-y-3">
        {comments.map((c, idx) => (
          <li
            key={`${idx}-${c.comment_text.slice(0, 20)}`}
            className="rounded border border-border bg-muted/40 p-2 space-y-2"
          >
            <Label className="text-xs">Comment {idx + 1}</Label>
            <Textarea
              value={c.comment_text}
              onChange={(e) =>
                updateComment(idx, { comment_text: e.target.value })
              }
              rows={3}
              data-testid={`rr-comment-text-${row.id}-${idx}`}
            />
            <Label className="text-xs">Response (HTML)</Label>
            <Textarea
              value={c.response_html}
              onChange={(e) =>
                updateComment(idx, { response_html: e.target.value })
              }
              rows={4}
              data-testid={`rr-comment-response-${row.id}-${idx}`}
            />
          </li>
        ))}
      </ul>
    </div>
  )
}
