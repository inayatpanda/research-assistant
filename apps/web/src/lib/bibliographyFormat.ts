import type { Article } from './api'

/** Vancouver-style author list: 'Last F, Last F, et al.' Caps at 6 authors. */
function authorList(authors: string[]): string {
  if (!authors || authors.length === 0) return 'Anonymous'
  const formatted: string[] = []
  for (const a of authors.slice(0, 6)) {
    const parts = (a || '').trim().split(/\s+/)
    if (!parts.length) continue
    const last = parts[parts.length - 1]
    const initials = parts
      .slice(0, -1)
      .map((p) => p[0]?.toUpperCase())
      .filter(Boolean)
      .join('')
    formatted.push(initials ? `${last} ${initials}` : last)
  }
  if (authors.length > 6) formatted.push('et al.')
  return formatted.join(', ')
}

/** Single Vancouver reference-list entry. Mirrors the server-side formatter. */
export function bibliographyEntry(article: Article, number?: number): string {
  const prefix = number != null ? `${number}. ` : ''
  const authors = authorList(article.authors)
  const title = (article.title || 'Untitled').replace(/\.$/, '')
  const year = article.year ? String(article.year) : 'n.d.'
  let issueBlock = ''
  if (article.volume) {
    issueBlock = article.volume
    if (article.issue) issueBlock += `(${article.issue})`
    if (article.pages) issueBlock += `:${article.pages}`
  } else if (article.pages) {
    issueBlock = article.pages
  }
  const parts: string[] = [`${prefix}${authors}.`, `${title}.`]
  if (article.journal) parts.push(`${article.journal}.`)
  let tail = year
  if (issueBlock) tail += `;${issueBlock}`
  parts.push(`${tail}.`)
  if (article.doi) parts.push(`doi:${article.doi}`)
  return parts.join(' ')
}
