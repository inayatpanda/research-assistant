import { NodeViewWrapper, type ReactNodeViewProps } from '@tiptap/react'

import { useCitationNumbers } from '@/lib/tiptap/citationNumbers'

/**
 * React NodeView for the Citation node. Looks up the number from the global
 * `useCitationNumbers` store keyed by `articleId`. Renders `[N]` (or `[?]` if
 * not in the map yet).
 */
export function CitationNodeView({ node }: ReactNodeViewProps) {
  const articleId: string | null = node.attrs.articleId
  const number = useCitationNumbers((s) =>
    articleId ? s.map.get(articleId) ?? null : null,
  )
  const label = number != null ? `[${number}]` : articleId ? '[…]' : '[?]'
  return (
    <NodeViewWrapper as="sup" className="citation" data-citation="true">
      {label}
    </NodeViewWrapper>
  )
}
