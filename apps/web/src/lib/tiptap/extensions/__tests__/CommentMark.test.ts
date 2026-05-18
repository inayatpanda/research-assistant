import { describe, expect, it } from 'vitest'

import { CommentMark } from '../CommentMark'

describe('CommentMark extension', () => {
  it('is registered as a Mark named "comment"', () => {
    expect(CommentMark.name).toBe('comment')
    expect(CommentMark.type).toBe('mark')
  })

  it('declares commentId as a configurable attribute', () => {
    const cfg = CommentMark.config.addAttributes?.call(CommentMark as never)
    expect(cfg).toBeDefined()
    expect((cfg as { commentId?: unknown }).commentId).toBeDefined()
  })

  it('renderHTML emits a span with data-comment-id', () => {
    const rendered = CommentMark.config.renderHTML?.call(
      CommentMark as never,
      {
        HTMLAttributes: { 'data-comment-id': 'cmt-1' },
        mark: {
          type: { name: 'comment' },
          attrs: { commentId: 'cmt-1' },
        } as never,
      } as never,
    )
    expect(rendered).toBeDefined()
    // tiptap render arrays start with the tag name.
    const arr = rendered as unknown[]
    expect(arr[0]).toBe('span')
    const attrs = arr[1] as Record<string, string>
    expect(attrs['data-comment']).toBe('true')
    expect(attrs['data-comment-id']).toBe('cmt-1')
  })
})
