/**
 * Phase 11 — Right-rail comments panel.
 *
 * Lists margin comments scoped to a section (or all sections). Click a
 * row to scroll the bound TipTap editor to the anchored range; if the
 * anchor falls outside the current doc length the row gets a
 * "(anchor stale)" badge — text has drifted past where the comment was
 * originally placed.
 *
 * Comment bodies are user-supplied free text; render through DOMPurify
 * even though we set them as text content (defence-in-depth).
 */
import DOMPurify from 'dompurify'
import { useState } from 'react'
import type { Editor } from '@tiptap/react'
import { toast } from 'sonner'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  useComments,
  useDeleteComment,
  useUpdateComment,
} from '@/hooks/useComments'
import type { CommentSection } from '@/lib/api'

type Props = {
  projectId: string
  /** When provided, the rail filters to comments anchored in this section. */
  activeSection?: CommentSection
  /** When provided, clicking a comment scrolls the editor to the anchor. */
  editor?: Editor | null
}

function sanitizeBody(body: string): string {
  // Comments are plain user text — strip ANY tags before display.
  return DOMPurify.sanitize(body, { ALLOWED_TAGS: [], ALLOWED_ATTR: [] })
}

export function CommentsRail({ projectId, activeSection, editor }: Props) {
  const [open, setOpen] = useState(true)
  const filter = activeSection ? { section: activeSection } : undefined
  const { data: all = [], isLoading } = useComments(projectId, filter)
  const update = useUpdateComment(projectId)
  const remove = useDeleteComment(projectId)

  // Split into open vs resolved so the rail shows live notes at the top.
  const openComments = all.filter((c) => !c.resolved)
  const resolvedComments = all.filter((c) => c.resolved)

  function docLength(): number | null {
    if (!editor) return null
    try {
      return editor.state.doc.content.size
    } catch {
      return null
    }
  }

  function handleJump(start: number, end: number) {
    if (!editor) return
    const len = docLength()
    if (len === null) return
    if (start >= len || end > len + 1) {
      toast.message('Comment anchor is no longer in this section')
      return
    }
    try {
      editor.commands.focus()
      editor.commands.setTextSelection({
        from: Math.max(0, start),
        to: Math.min(len, end),
      })
      editor.commands.scrollIntoView()
    } catch {
      // Anchor invalid — surface as stale.
      toast.message('Could not jump to comment anchor')
    }
  }

  return (
    <Card data-testid="comments-rail">
      <CardHeader className="pb-2">
        <button
          type="button"
          className="text-left w-full"
          onClick={() => setOpen((v) => !v)}
          data-testid="comments-rail-toggle"
        >
          <CardTitle className="text-[13px] font-medium">
            Comments {open ? '▾' : '▸'} ({openComments.length})
          </CardTitle>
        </button>
        <CardDescription className="text-[11px]">
          {activeSection
            ? `Notes anchored in ${activeSection}`
            : 'Notes across the manuscript'}
        </CardDescription>
      </CardHeader>
      {open && (
        <CardContent className="pt-0">
          {isLoading ? (
            <div className="text-[12px] text-muted-foreground">Loading…</div>
          ) : all.length === 0 ? (
            <div className="text-[12px] text-muted-foreground">
              No comments yet. Select text in the editor and click
              &ldquo;Comment&rdquo; to add one.
            </div>
          ) : (
            <ScrollArea className="max-h-[320px]">
              <ul className="space-y-2">
                {openComments.map((c) => {
                  const len = docLength()
                  const stale =
                    activeSection === c.section_name &&
                    len !== null &&
                    (c.anchor_start >= len || c.anchor_end > len + 1)
                  const body = sanitizeBody(c.body)
                  return (
                    <li
                      key={c.id}
                      className="rounded border border-border bg-white p-2"
                      data-testid={`comment-row-${c.id}`}
                    >
                      <div className="flex items-center justify-between gap-2 mb-1">
                        <Badge variant="outline" className="text-[10px]">
                          {c.section_name}
                        </Badge>
                        {stale ? (
                          <Badge
                            variant="outline"
                            className="text-[10px] text-amber-600 border-amber-400"
                            data-testid={`comment-stale-${c.id}`}
                          >
                            (anchor stale)
                          </Badge>
                        ) : null}
                      </div>
                      <button
                        type="button"
                        className="text-[12px] text-left w-full hover:underline"
                        onClick={() =>
                          handleJump(c.anchor_start, c.anchor_end)
                        }
                        data-testid={`comment-jump-${c.id}`}
                      >
                        {body}
                      </button>
                      <div className="mt-1 flex items-center gap-2">
                        <Button
                          size="sm"
                          variant="ghost"
                          className="h-5 px-1 text-[11px]"
                          onClick={() =>
                            update.mutate({
                              id: c.id,
                              body: { resolved: true },
                            })
                          }
                          data-testid={`comment-resolve-${c.id}`}
                        >
                          Resolve
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          className="h-5 px-1 text-[11px] text-rose-600"
                          onClick={() => remove.mutate(c.id)}
                          data-testid={`comment-delete-${c.id}`}
                        >
                          Delete
                        </Button>
                      </div>
                    </li>
                  )
                })}
                {resolvedComments.length > 0 ? (
                  <li className="pt-2 border-t border-border">
                    <details>
                      <summary className="text-[11px] text-muted-foreground cursor-pointer">
                        Resolved ({resolvedComments.length})
                      </summary>
                      <ul className="space-y-2 mt-2">
                        {resolvedComments.map((c) => (
                          <li
                            key={c.id}
                            className="rounded border border-border bg-zinc-50 p-2 opacity-70"
                            data-testid={`comment-resolved-${c.id}`}
                          >
                            <Badge
                              variant="outline"
                              className="text-[10px] mb-1"
                            >
                              {c.section_name}
                            </Badge>
                            <div className="text-[12px]">
                              {sanitizeBody(c.body)}
                            </div>
                            <Button
                              size="sm"
                              variant="ghost"
                              className="h-5 px-1 text-[11px] mt-1"
                              onClick={() =>
                                update.mutate({
                                  id: c.id,
                                  body: { resolved: false },
                                })
                              }
                            >
                              Reopen
                            </Button>
                          </li>
                        ))}
                      </ul>
                    </details>
                  </li>
                ) : null}
              </ul>
            </ScrollArea>
          )}
        </CardContent>
      )}
    </Card>
  )
}
