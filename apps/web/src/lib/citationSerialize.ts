/**
 * HTML <-> CITE token round-trip for the AI writing-assist boundary.
 *
 * Going OUT to the AI:
 *   <sup data-citation data-article-id="abc">[N]</sup>  →  [CITE_abc]
 *
 * Coming BACK from the AI (which is told to preserve those tokens), we reverse
 * the mapping. Tokens whose articleId isn't in the document context are left
 * as literal text — same contract as the backend's citation_format service.
 */

const SUP_RE =
  /<sup\b[^>]*?\bdata-citation\b[^>]*?\bdata-article-id="([^"]+)"[^>]*>(.*?)<\/sup>/gi

const SUP_RE_REV =
  /<sup\b[^>]*?\bdata-article-id="([^"]+)"[^>]*?\bdata-citation\b[^>]*>(.*?)<\/sup>/gi

const CITE_TOKEN_RE = /\[CITE_([A-Za-z0-9_-]+)\]/g

/** Convert HTML with <sup data-citation> markers into a string where each marker
 *  is replaced by [CITE_<articleId>]. Other tags + text are preserved verbatim. */
export function htmlToAiSafeText(html: string): string {
  if (!html) return ''
  let out = html.replace(SUP_RE, (_full, articleId: string) => `[CITE_${articleId}]`)
  // Belt-and-braces — the attribute order can vary by serializer
  out = out.replace(SUP_RE_REV, (_full, articleId: string) => `[CITE_${articleId}]`)
  return out
}

/** Reverse: convert [CITE_<articleId>] back into <sup> markers, *only* for
 *  articleIds that are valid in the current document context. Unknown tokens
 *  remain as literal text. */
export function aiSafeTextToHtml(
  text: string,
  validArticleIds: Set<string>,
): string {
  if (!text) return ''
  return text.replace(CITE_TOKEN_RE, (full, articleId: string) => {
    if (!validArticleIds.has(articleId)) return full
    return `<sup data-citation="true" class="citation" data-article-id="${articleId}">[…]</sup>`
  })
}
