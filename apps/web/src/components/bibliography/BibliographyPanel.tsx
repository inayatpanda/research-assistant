import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { BookText } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useMemo, useState } from 'react'
import { toast } from 'sonner'

import {
  articlesApi,
  bibliographyApi,
  exportApi,
  projectsApi,
  type BibliographyEntry,
  type CitationStyle,
  type PersistedCitationStyle,
} from '@/lib/api'
import { toBibTeX, toCSLJSON, toRIS } from '@/lib/bibliographyFormat'

import { BibliographyRow } from './BibliographyRow'
import { BibliographyToolbar } from './BibliographyToolbar'

const PERSISTABLE_STYLES: ReadonlySet<CitationStyle> = new Set([
  'vancouver',
  'apa',
  'harvard',
])

function downloadText(filename: string, mime: string, body: string) {
  const blob = new Blob([body], { type: mime })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 0)
}

export function BibliographyPanel({ projectId }: { projectId: string }) {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [override, setOverride] = useState<CitationStyle | null>(null)
  const [busyExport, setBusyExport] = useState<'docx' | 'pdf' | null>(null)

  const { data: project } = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => projectsApi.get(projectId),
  })
  const projectStyle: CitationStyle = project?.citation_style ?? 'vancouver'
  const activeStyle: CitationStyle = override ?? projectStyle

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['bibliography', projectId, activeStyle],
    queryFn: () => bibliographyApi.get(projectId, activeStyle),
  })

  const { data: articles = [] } = useQuery({
    queryKey: ['articles', projectId],
    queryFn: () => articlesApi.list(projectId),
  })

  const persistStyle = useMutation({
    mutationFn: (next: PersistedCitationStyle) =>
      projectsApi.update(projectId, { citation_style: next }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['project', projectId] }),
  })

  const entries: BibliographyEntry[] = useMemo(() => data?.entries ?? [], [data])
  const isEmpty = !isLoading && entries.length === 0

  const handleStyleChange = (next: CitationStyle) => {
    setOverride(next)
    if (PERSISTABLE_STYLES.has(next) && next !== projectStyle) {
      persistStyle.mutate(next as PersistedCitationStyle)
    }
  }

  const copyToClipboard = async (text: string, successMsg: string) => {
    try {
      await navigator.clipboard.writeText(text)
      toast.success(successMsg)
    } catch {
      toast.error('Could not copy to clipboard')
    }
  }

  const handleCopyAll = () => {
    if (!entries.length) return
    const joined = entries.map((e) => e.formatted_entry).join('\n\n')
    void copyToClipboard(joined, `Copied ${entries.length} reference${entries.length === 1 ? '' : 's'}`)
  }

  const handleCopyOne = (entry: BibliographyEntry) => {
    void copyToClipboard(entry.formatted_entry, 'Reference copied')
  }

  const handleLocate = (entry: BibliographyEntry) => {
    const section = entry.first_section || 'Introduction'
    const params = new URLSearchParams()
    params.set('section', section)
    params.set('scrollTo', `cite-${entry.article_id}`)
    navigate(`/projects/${projectId}/manuscript?${params.toString()}`, {
      replace: true,
    })
  }

  /** Resolve the article list to the bibliography order so client-side exports
   * (BibTeX/RIS/CSL-JSON) line up with [N] numbering. */
  const orderedArticles = useMemo(() => {
    const byId = new Map(articles.map((a) => [a.id, a]))
    return entries
      .map((e) => byId.get(e.article_id))
      .filter((a): a is NonNullable<typeof a> => Boolean(a))
  }, [articles, entries])

  const handleExport = async (kind: 'docx' | 'pdf' | 'bibtex' | 'ris' | 'csl-json') => {
    const slug = (project?.title ?? 'manuscript')
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/(^-|-$)+/g, '')
      .slice(0, 40) || 'manuscript'
    try {
      if (kind === 'docx') {
        setBusyExport('docx')
        const filename = await exportApi.downloadDocx(projectId, slug)
        toast.success(`Downloaded ${filename}`)
      } else if (kind === 'pdf') {
        setBusyExport('pdf')
        const filename = await exportApi.downloadPdf(projectId, slug)
        toast.success(`Downloaded ${filename}`)
      } else if (kind === 'bibtex') {
        downloadText(`${slug}.bib`, 'application/x-bibtex', toBibTeX(orderedArticles))
        toast.success('BibTeX downloaded')
      } else if (kind === 'ris') {
        downloadText(`${slug}.ris`, 'application/x-research-info-systems', toRIS(orderedArticles))
        toast.success('RIS downloaded')
      } else {
        downloadText(`${slug}.json`, 'application/vnd.citationstyles.csl+json', toCSLJSON(orderedArticles))
        toast.success('CSL-JSON downloaded')
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Export failed'
      toast.error(msg)
    } finally {
      setBusyExport(null)
    }
  }

  return (
    <div className="rounded-md border border-border bg-white p-4 space-y-3">
      <div className="flex items-center gap-2">
        <BookText className="h-4 w-4 text-muted-foreground" />
        <div className="text-[13px] font-semibold tracking-tight">Bibliography</div>
        {entries.length > 0 && (
          <span className="ml-auto text-[11px] text-muted-foreground tabular-nums">
            {entries.length}
          </span>
        )}
      </div>

      <BibliographyToolbar
        style={activeStyle}
        onStyleChange={handleStyleChange}
        onCopyAll={handleCopyAll}
        onExport={handleExport}
        busyExport={busyExport}
        disabled={isLoading || isEmpty}
      />

      {isLoading && (
        <div className="text-[12px] text-muted-foreground italic">Loading references…</div>
      )}
      {isError && (
        <div className="text-[12px] text-rose-700">
          {(error as Error)?.message ?? 'Failed to load bibliography'}
        </div>
      )}
      {isEmpty && !isError && (
        <div className="text-[12px] text-muted-foreground italic">
          No references yet. Add citations in the manuscript and they will appear here in citation order.
        </div>
      )}
      {entries.length > 0 && (
        <ul className="space-y-0 max-h-[420px] overflow-y-auto pr-1">
          {entries.map((e) => (
            <BibliographyRow
              key={`${e.article_id}-${e.number}`}
              entry={e}
              onCopy={handleCopyOne}
              onLocate={handleLocate}
            />
          ))}
        </ul>
      )}
    </div>
  )
}
