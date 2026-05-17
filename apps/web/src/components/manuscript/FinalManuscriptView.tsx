import { useQuery } from '@tanstack/react-query'
import { useEffect, useMemo, useRef } from 'react'

import { articlesApi, manuscriptApi, type ManuscriptSectionName } from '@/lib/api'
import { bibliographyEntry } from '@/lib/bibliographyFormat'
import { numberCitationsAcross } from '@/lib/tiptap/citationEngine'

const SECTION_ORDER: ManuscriptSectionName[] = [
  'Abstract',
  'Introduction',
  'Methodology',
  'Results',
  'Discussion',
  'Conclusion',
]

export function FinalManuscriptView({ projectId }: { projectId: string }) {
  const sectionQueries = SECTION_ORDER.map((section) =>
    useQuery({
      queryKey: ['manuscript-section', projectId, section],
      queryFn: () => manuscriptApi.getSection(projectId, section),
    }),
  )
  const { data: articles = [] } = useQuery({
    queryKey: ['articles', projectId],
    queryFn: () => articlesApi.list(projectId),
  })

  const htmlBySection = useMemo(() => {
    const out: Record<ManuscriptSectionName, string> = {} as Record<
      ManuscriptSectionName,
      string
    >
    SECTION_ORDER.forEach((s, i) => {
      out[s] = sectionQueries[i].data?.content ?? ''
    })
    return out
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sectionQueries.map((q) => q.data?.content).join('|')])

  // Single continuous numbering across all sections
  const numbers = useMemo(
    () => numberCitationsAcross(SECTION_ORDER.map((s) => htmlBySection[s] || '')),
    [htmlBySection],
  )

  // Replace [...]/[?] inside each section's <sup data-citation> with [N]
  const renderedHtml = useMemo(() => {
    return SECTION_ORDER.map((s) => {
      const raw = htmlBySection[s] || ''
      if (!raw) return ''
      return raw.replace(
        /(<sup\b[^>]*?\bdata-citation\b[^>]*?)>(\[.*?\])<\/sup>/gi,
        (_full, openTag: string) => {
          const idMatch = /data-article-id="([^"]+)"/.exec(openTag)
          const id = idMatch?.[1]
          const n = id ? numbers.get(id) : undefined
          return `${openTag}>[${n ?? '?'}]</sup>`
        },
      )
    })
  }, [htmlBySection, numbers])

  const cited = useMemo(() => {
    const ids = Array.from(numbers.keys())
    return ids
      .map((id) => articles.find((a) => a.id === id))
      .filter((a): a is NonNullable<typeof a> => !!a)
  }, [numbers, articles])

  const printRef = useRef<HTMLDivElement>(null)
  useEffect(() => {
    // No-op: kept for future "Export to .docx" hook
  }, [printRef])

  return (
    <div className="flex-1 min-h-0 overflow-y-auto bg-white">
      <div
        ref={printRef}
        className="mx-auto max-w-[720px] px-10 py-14 font-serif text-[16px] leading-[28px]"
      >
        {SECTION_ORDER.map((s, i) => {
          const html = renderedHtml[i]
          if (!html) {
            return (
              <section key={s} className="mb-10">
                <h2 className="font-sans text-[14px] uppercase tracking-wider text-muted-foreground mt-8 mb-3">
                  {s}
                </h2>
                <p className="text-muted-foreground italic text-[14px]">
                  (Empty — write this section in the editor.)
                </p>
              </section>
            )
          }
          return (
            <section key={s} className="mb-10">
              <h2 className="font-sans text-[14px] uppercase tracking-wider text-muted-foreground mt-8 mb-3">
                {s}
              </h2>
              <div className="manuscript-prose" dangerouslySetInnerHTML={{ __html: html }} />
            </section>
          )
        })}

        {cited.length > 0 && (
          <section className="mt-12 border-t border-border pt-6">
            <h2 className="font-sans text-[14px] uppercase tracking-wider text-muted-foreground mb-4">
              References
            </h2>
            <ol className="list-none p-0 space-y-3 text-[14px] leading-[22px]">
              {cited.map((a, idx) => (
                <li key={a.id} className="flex gap-2">
                  <span className="tabular-nums text-muted-foreground shrink-0 w-7">
                    {idx + 1}.
                  </span>
                  <span>{bibliographyEntry(a)}</span>
                </li>
              ))}
            </ol>
          </section>
        )}
      </div>
    </div>
  )
}
