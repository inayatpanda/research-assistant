import type { Article, CitationStyle } from './api'

// --- Author-list formatters mirroring services/citation_format.py ---

const EN_DASH = '–'

function splitName(name: string): { last: string; given: string[] } {
  const parts = (name ?? '').trim().split(/\s+/).filter(Boolean)
  if (!parts.length) return { last: '', given: [] }
  return { last: parts[parts.length - 1], given: parts.slice(0, -1) }
}

function initialsBare(parts: string[]): string {
  return parts
    .map((p) => p[0]?.toUpperCase() ?? '')
    .filter(Boolean)
    .join('')
}

function initialsDotted(parts: string[]): string {
  return parts
    .filter(Boolean)
    .map((p) => `${p[0]?.toUpperCase() ?? ''}.`)
    .join(' ')
}

function normalisePages(pages: string | null | undefined): string | null {
  if (!pages) return null
  return pages.replace(/-/g, EN_DASH)
}

/** Vancouver: 'Last F, Last F, et al.' Caps at 6 authors. */
function authorListVancouver(authors: string[]): string {
  if (!authors || authors.length === 0) return 'Anonymous'
  const out: string[] = []
  for (const a of authors.slice(0, 6)) {
    const { last, given } = splitName(a)
    if (!last) continue
    const ini = initialsBare(given)
    out.push(ini ? `${last} ${ini}` : last)
  }
  if (authors.length > 6) out.push('et al.')
  return out.join(', ')
}

/** APA 7: 'Last, F. M., Last, F., & Last, F.'  ≤20 list all, 21+ first 19 + ellipsis + last. */
function authorListAPA(authors: string[]): string {
  if (!authors || authors.length === 0) return 'Anonymous'
  const formatted: string[] = []
  for (const a of authors) {
    const { last, given } = splitName(a)
    if (!last) continue
    const ini = initialsDotted(given)
    formatted.push(ini ? `${last}, ${ini}` : last)
  }
  if (!formatted.length) return 'Anonymous'
  if (formatted.length === 1) return formatted[0]
  if (formatted.length <= 20) {
    return formatted.slice(0, -1).join(', ') + `, & ${formatted[formatted.length - 1]}`
  }
  const head = formatted.slice(0, 19).join(', ')
  return `${head}, ... ${formatted[formatted.length - 1]}`
}

/** Harvard: 1 → 'Doe, J.', 2 → 'Doe, J. and Smith, J.', 3+ → 'Doe, J. et al.' */
function authorListHarvard(authors: string[]): string {
  if (!authors || authors.length === 0) return 'Anon.'
  const formatted: string[] = []
  for (const a of authors.slice(0, 3)) {
    const { last, given } = splitName(a)
    if (!last) continue
    const ini = initialsDotted(given)
    formatted.push(ini ? `${last}, ${ini}` : last)
  }
  if (!formatted.length) return 'Anon.'
  if (authors.length >= 3 && formatted.length >= 1) return `${formatted[0]} et al.`
  if (formatted.length === 1) return formatted[0]
  return `${formatted[0]} and ${formatted[1]}`
}

/** IEEE: 'F. Last' / 'F. Last and F. Last' / 'F. Last, F. Last, and F. Last' / 'F. Last et al.' */
function authorListIEEE(authors: string[]): string {
  if (!authors || authors.length === 0) return 'Anonymous'
  const formatted: string[] = []
  for (const a of authors.slice(0, 3)) {
    const { last, given } = splitName(a)
    if (!last) continue
    const ini = initialsDotted(given)
    formatted.push(ini ? `${ini} ${last}` : last)
  }
  if (!formatted.length) return 'Anonymous'
  if (authors.length >= 4) return `${formatted[0]} et al.`
  if (formatted.length === 1) return formatted[0]
  if (formatted.length === 2) return `${formatted[0]} and ${formatted[1]}`
  return `${formatted[0]}, ${formatted[1]}, and ${formatted[2]}`
}

// --- Per-style entry formatters (plain text) ---

/** Vancouver reference-list entry. Numbered when `number` is provided. */
export function vancouverEntry(article: Article, number?: number): string {
  const prefix = number != null ? `${number}. ` : ''
  const authors = authorListVancouver(article.authors)
  const title = (article.title || 'Untitled').replace(/\.$/, '')
  const journal = article.journal || ''
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
  if (journal) parts.push(`${journal}.`)
  let tail = year
  if (issueBlock) tail += `;${issueBlock}`
  parts.push(`${tail}.`)
  if (article.doi) parts.push(`doi:${article.doi}`)
  return parts.join(' ')
}

export function apaEntry(article: Article): string {
  const authors = authorListAPA(article.authors)
  const title = (article.title || 'Untitled').replace(/\.$/, '')
  const journal = article.journal || ''
  const year = article.year ? String(article.year) : 'n.d.'
  const pages = normalisePages(article.pages)
  const authorSep = authors.endsWith('.') ? '' : '.'
  let out = `${authors}${authorSep} (${year}). ${title}.`
  if (journal) {
    out += ` ${journal}`
    if (article.volume) {
      out += `, ${article.volume}`
      if (article.issue) out += `(${article.issue})`
      if (pages) out += `, ${pages}`
    } else if (pages) {
      out += `, ${pages}`
    }
    out += '.'
  }
  if (article.doi) out += ` https://doi.org/${article.doi}`
  return out
}

export function harvardEntry(article: Article): string {
  const authors = authorListHarvard(article.authors)
  const title = (article.title || 'Untitled').replace(/\.$/, '')
  const journal = article.journal || ''
  const year = article.year ? String(article.year) : 'n.d.'
  const pages = normalisePages(article.pages)
  let out = `${authors} (${year}) '${title}'`
  if (journal) {
    out += `, ${journal}`
    if (article.volume) {
      out += `, ${article.volume}`
      if (article.issue) out += `(${article.issue})`
    }
    if (pages) out += `, pp. ${pages}`
  }
  out += '.'
  if (article.doi) out += ` doi:${article.doi}`
  return out
}

export function ieeeEntry(article: Article, number?: number): string {
  const authors = authorListIEEE(article.authors)
  const title = (article.title || 'Untitled').replace(/\.$/, '')
  const journal = article.journal || ''
  const pages = normalisePages(article.pages)
  const year = article.year ? String(article.year) : null
  let out = `${authors}, "${title},"`
  const tail: string[] = []
  if (journal) tail.push(journal)
  if (article.volume) {
    tail.push(`vol. ${article.volume}`)
    if (article.issue) tail.push(`no. ${article.issue}`)
  }
  if (pages) tail.push(`pp. ${pages}`)
  if (year) tail.push(year)
  if (tail.length) out += ' ' + tail.join(', ')
  if (article.doi) out += `, doi: ${article.doi}`
  const body = out + '.'
  return number != null ? `[${number}] ${body}` : body
}

/** Style-dispatching reference-list entry. */
export function bibliographyEntry(
  article: Article,
  number?: number,
  style: CitationStyle = 'vancouver',
): string {
  switch (style) {
    case 'apa':
      return apaEntry(article)
    case 'harvard':
      return harvardEntry(article)
    case 'ieee':
      return ieeeEntry(article, number)
    case 'vancouver':
    default:
      return vancouverEntry(article, number)
  }
}

// --- Reference-manager format converters (client-side only) ---

function bibtexEscape(value: string): string {
  // Brace special characters so BibTeX parsers don't interpret them.
  return value.replace(/[\\{}%&$_#^~]/g, (c) => `{${c}}`)
}

function bibtexKey(article: Article, index: number): string {
  const firstAuthor = article.authors?.[0] ?? ''
  const last = splitName(firstAuthor).last || 'ref'
  const safeLast = last.replace(/[^A-Za-z0-9]/g, '')
  const year = article.year ?? index
  return `${safeLast || 'ref'}${year}`
}

/** Approximate BibTeX serialisation. Good enough for Zotero / Mendeley import. */
export function toBibTeX(articles: Article[]): string {
  const out: string[] = []
  articles.forEach((a, i) => {
    const key = bibtexKey(a, i + 1)
    const type = a.journal ? 'article' : 'misc'
    const fields: Array<[string, string | null]> = [
      ['author', a.authors?.length ? a.authors.map(bibtexEscape).join(' and ') : null],
      ['title', a.title ? `{${bibtexEscape(a.title)}}` : null],
      ['journal', a.journal ? bibtexEscape(a.journal) : null],
      ['year', a.year != null ? String(a.year) : null],
      ['volume', a.volume ? bibtexEscape(a.volume) : null],
      ['number', a.issue ? bibtexEscape(a.issue) : null],
      ['pages', a.pages ? bibtexEscape(a.pages).replace(/-/g, '--') : null],
      ['doi', a.doi ?? null],
    ]
    const body = fields
      .filter((f): f is [string, string] => f[1] != null && f[1] !== '')
      .map(([k, v]) => `  ${k} = {${v}}`)
      .join(',\n')
    out.push(`@${type}{${key},\n${body}\n}`)
  })
  return out.join('\n\n') + (out.length ? '\n' : '')
}

/** Approximate RIS serialisation. Good enough for Zotero / Mendeley import. */
export function toRIS(articles: Article[]): string {
  const lines: string[] = []
  articles.forEach((a) => {
    lines.push(`TY  - ${a.journal ? 'JOUR' : 'GEN'}`)
    for (const author of a.authors ?? []) {
      lines.push(`AU  - ${author}`)
    }
    if (a.title) lines.push(`TI  - ${a.title}`)
    if (a.journal) lines.push(`T2  - ${a.journal}`)
    if (a.year != null) lines.push(`PY  - ${a.year}`)
    if (a.volume) lines.push(`VL  - ${a.volume}`)
    if (a.issue) lines.push(`IS  - ${a.issue}`)
    if (a.pages) {
      const parts = a.pages.split('-')
      lines.push(`SP  - ${parts[0]?.trim() ?? ''}`)
      if (parts.length > 1) lines.push(`EP  - ${parts[1].trim()}`)
    }
    if (a.doi) lines.push(`DO  - ${a.doi}`)
    lines.push('ER  - ')
    lines.push('')
  })
  return lines.join('\n')
}

/** CSL-JSON serialisation. */
export function toCSLJSON(articles: Article[]): string {
  const items = articles.map((a, i) => {
    const author = (a.authors ?? []).map((name) => {
      const { last, given } = splitName(name)
      return given.length ? { family: last, given: given.join(' ') } : { family: last || name }
    })
    const item: Record<string, unknown> = {
      id: a.id || `ref-${i + 1}`,
      type: a.journal ? 'article-journal' : 'document',
    }
    if (a.title) item.title = a.title
    if (a.journal) item['container-title'] = a.journal
    if (author.length) item.author = author
    if (a.year != null) item.issued = { 'date-parts': [[a.year]] }
    if (a.volume) item.volume = a.volume
    if (a.issue) item.issue = a.issue
    if (a.pages) item.page = a.pages
    if (a.doi) item.DOI = a.doi
    return item
  })
  return JSON.stringify(items, null, 2)
}
