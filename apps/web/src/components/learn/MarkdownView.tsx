/**
 * Phase 5a — minimal inline Markdown renderer.
 *
 * Avoids pulling in `react-markdown` (not in deps) for the small subset
 * needed by Learn entries: headings (#/##/###), paragraphs, unordered
 * lists, ordered lists, blockquotes, inline `code`, bold (**…**), italics
 * (*…*) and inline-code blocks. Stat-test entries deliberately use this
 * subset; richer Markdown (images, tables, links to other entries) is
 * Phase 5b/5c work.
 *
 * Rendering is React-only — no `dangerouslySetInnerHTML`, no DOM string
 * concatenation — so there is no XSS attack surface even with curated
 * content that travels through the API.
 */
import * as React from 'react'

interface Props {
  source: string
  className?: string
}

interface Block {
  type: 'h1' | 'h2' | 'h3' | 'p' | 'ul' | 'ol' | 'blockquote'
  lines: string[]
}

function parseBlocks(src: string): Block[] {
  const lines = src.replace(/\r\n/g, '\n').split('\n')
  const blocks: Block[] = []
  let current: Block | null = null

  const flush = () => {
    if (current) {
      blocks.push(current)
      current = null
    }
  }

  for (const raw of lines) {
    const line = raw.replace(/\s+$/, '')
    if (!line.trim()) {
      flush()
      continue
    }
    if (line.startsWith('### ')) {
      flush()
      blocks.push({ type: 'h3', lines: [line.slice(4)] })
      continue
    }
    if (line.startsWith('## ')) {
      flush()
      blocks.push({ type: 'h2', lines: [line.slice(3)] })
      continue
    }
    if (line.startsWith('# ')) {
      flush()
      blocks.push({ type: 'h1', lines: [line.slice(2)] })
      continue
    }
    if (/^\s*[-*]\s+/.test(line)) {
      if (!current || current.type !== 'ul') {
        flush()
        current = { type: 'ul', lines: [] }
      }
      current.lines.push(line.replace(/^\s*[-*]\s+/, ''))
      continue
    }
    if (/^\s*\d+\.\s+/.test(line)) {
      if (!current || current.type !== 'ol') {
        flush()
        current = { type: 'ol', lines: [] }
      }
      current.lines.push(line.replace(/^\s*\d+\.\s+/, ''))
      continue
    }
    if (line.startsWith('> ')) {
      if (!current || current.type !== 'blockquote') {
        flush()
        current = { type: 'blockquote', lines: [] }
      }
      current.lines.push(line.slice(2))
      continue
    }
    if (!current || current.type !== 'p') {
      flush()
      current = { type: 'p', lines: [] }
    }
    current.lines.push(line)
  }
  flush()
  return blocks
}

/** Render inline ** *  `…` markup as React nodes — no innerHTML. */
function renderInline(text: string, keyPrefix: string): React.ReactNode[] {
  // Tokenise into runs of code/bold/italic/text.
  const out: React.ReactNode[] = []
  let i = 0
  let k = 0
  while (i < text.length) {
    if (text[i] === '`') {
      const end = text.indexOf('`', i + 1)
      if (end > -1) {
        out.push(
          <code
            key={`${keyPrefix}-c${k++}`}
            className="rounded bg-muted px-1 py-0.5 text-[12px] font-mono"
          >
            {text.slice(i + 1, end)}
          </code>,
        )
        i = end + 1
        continue
      }
    }
    if (text.startsWith('**', i)) {
      const end = text.indexOf('**', i + 2)
      if (end > -1) {
        out.push(
          <strong key={`${keyPrefix}-b${k++}`} className="font-semibold">
            {text.slice(i + 2, end)}
          </strong>,
        )
        i = end + 2
        continue
      }
    }
    if (text[i] === '*' && text[i + 1] !== ' ') {
      const end = text.indexOf('*', i + 1)
      if (end > -1) {
        out.push(
          <em key={`${keyPrefix}-i${k++}`} className="italic">
            {text.slice(i + 1, end)}
          </em>,
        )
        i = end + 1
        continue
      }
    }
    // Plain run: read until next markup-sensitive character.
    let j = i
    while (
      j < text.length &&
      text[j] !== '`' &&
      !(text[j] === '*' && (text[j + 1] === '*' || text[j + 1] !== ' '))
    ) {
      j++
    }
    if (j === i) j = i + 1
    out.push(<React.Fragment key={`${keyPrefix}-t${k++}`}>{text.slice(i, j)}</React.Fragment>)
    i = j
  }
  return out
}

export function MarkdownView({ source, className }: Props) {
  const blocks = React.useMemo(() => parseBlocks(source), [source])
  return (
    <div data-testid="markdown-view" className={className}>
      {blocks.map((b, idx) => {
        const key = `mdb-${idx}`
        if (b.type === 'h1') {
          return (
            <h1 key={key} className="mt-2 mb-3 text-2xl font-semibold tracking-tight">
              {renderInline(b.lines.join(' '), key)}
            </h1>
          )
        }
        if (b.type === 'h2') {
          return (
            <h2 key={key} className="mt-6 mb-2 text-lg font-semibold tracking-tight">
              {renderInline(b.lines.join(' '), key)}
            </h2>
          )
        }
        if (b.type === 'h3') {
          return (
            <h3 key={key} className="mt-4 mb-2 text-[15px] font-semibold">
              {renderInline(b.lines.join(' '), key)}
            </h3>
          )
        }
        if (b.type === 'ul') {
          return (
            <ul
              key={key}
              className="mt-2 mb-3 list-disc pl-6 space-y-1 text-[14px] leading-relaxed"
            >
              {b.lines.map((li, j) => (
                <li key={`${key}-li${j}`}>{renderInline(li, `${key}-li${j}`)}</li>
              ))}
            </ul>
          )
        }
        if (b.type === 'ol') {
          return (
            <ol
              key={key}
              className="mt-2 mb-3 list-decimal pl-6 space-y-1 text-[14px] leading-relaxed"
            >
              {b.lines.map((li, j) => (
                <li key={`${key}-li${j}`}>{renderInline(li, `${key}-li${j}`)}</li>
              ))}
            </ol>
          )
        }
        if (b.type === 'blockquote') {
          return (
            <blockquote
              key={key}
              className="mt-3 mb-3 border-l-2 border-border pl-4 text-[14px] italic text-muted-foreground"
            >
              {renderInline(b.lines.join(' '), key)}
            </blockquote>
          )
        }
        return (
          <p key={key} className="mt-2 mb-2 text-[14px] leading-relaxed">
            {renderInline(b.lines.join(' '), key)}
          </p>
        )
      })}
    </div>
  )
}
