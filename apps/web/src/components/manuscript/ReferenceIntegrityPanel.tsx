import { useQuery } from '@tanstack/react-query'
import { AlertTriangle, CheckCircle2 } from 'lucide-react'
import { useMemo } from 'react'

import { articlesApi, datasetsApi, manuscriptApi, type ManuscriptSectionName } from '@/lib/api'
import { numberCitationsAcross } from '@/lib/tiptap/citationEngine'

const SECTIONS: ManuscriptSectionName[] = [
  'Abstract',
  'Introduction',
  'Methodology',
  'Results',
  'Discussion',
  'Conclusion',
]

/** Citation ids prefixed `dataset_<uuid>` resolve against project datasets,
 * not the article library. Kept as a module-level constant so the prefix
 * lives in one place across FE + BE. */
const DATASET_CITATION_PREFIX = 'dataset_'

export function ReferenceIntegrityPanel({ projectId }: { projectId: string }) {
  const { data: articles = [] } = useQuery({
    queryKey: ['articles', projectId],
    queryFn: () => articlesApi.list(projectId),
  })

  const { data: datasets = [] } = useQuery({
    queryKey: ['datasets', projectId],
    queryFn: () => datasetsApi.list(projectId),
  })

  const sectionQueries = SECTIONS.map((s) =>
    useQuery({
      queryKey: ['manuscript-section', projectId, s],
      queryFn: () => manuscriptApi.getSection(projectId, s),
    }),
  )

  const issues = useMemo(() => {
    const htmls = SECTIONS.map((_, i) => sectionQueries[i].data?.content ?? '')
    const numbers = numberCitationsAcross(htmls)
    const citedIds = new Set(numbers.keys())
    const libraryIds = new Set(articles.map((a) => a.id))
    const datasetIds = new Set(datasets.map((d) => d.id))
    const orphanInline = [...citedIds].filter((id) => {
      // Dataset citations resolve against the project's datasets list, not
      // the article library — only flag them as orphan when the dataset id
      // itself is unknown.
      if (id.startsWith(DATASET_CITATION_PREFIX)) {
        return !datasetIds.has(id.slice(DATASET_CITATION_PREFIX.length))
      }
      return !libraryIds.has(id)
    })
    const uncitedLibrary = articles.filter((a) => !citedIds.has(a.id))
    return { orphanInline, uncitedLibrary, totalCited: citedIds.size }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [articles, datasets, sectionQueries.map((q) => q.data?.content).join('|')])

  const allClean = issues.orphanInline.length === 0 && issues.uncitedLibrary.length === 0

  return (
    <div className="rounded-md border border-border bg-white p-4 space-y-3">
      <div className="flex items-center gap-2">
        {allClean ? (
          <CheckCircle2 className="h-4 w-4 text-emerald-600" />
        ) : (
          <AlertTriangle className="h-4 w-4 text-amber-600" />
        )}
        <div className="text-[13px] font-semibold tracking-tight">Reference integrity</div>
      </div>
      <div className="text-[12px] text-muted-foreground">
        {issues.totalCited} reference{issues.totalCited === 1 ? '' : 's'} cited in the manuscript.
      </div>

      {issues.orphanInline.length > 0 && (
        <div>
          <div className="text-[11px] uppercase tracking-wider text-rose-700 font-medium">
            Citations pointing to articles not in your library
          </div>
          <ul className="mt-1 space-y-1 text-[12px]">
            {issues.orphanInline.map((id) => (
              <li key={id} className="text-rose-700 font-mono">
                {id.slice(0, 12)}…
              </li>
            ))}
          </ul>
        </div>
      )}

      {issues.uncitedLibrary.length > 0 && (
        <div>
          <div className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
            Library articles never cited
          </div>
          <ul className="mt-1 space-y-1 text-[12px]">
            {issues.uncitedLibrary.slice(0, 6).map((a) => (
              <li key={a.id} className="text-muted-foreground line-clamp-1">
                {a.title}
              </li>
            ))}
            {issues.uncitedLibrary.length > 6 && (
              <li className="text-[11px] text-muted-foreground italic">
                +{issues.uncitedLibrary.length - 6} more
              </li>
            )}
          </ul>
        </div>
      )}

      {allClean && (
        <div className="text-[12px] text-emerald-700">
          Every library article is cited; every citation points to a real article.
        </div>
      )}
    </div>
  )
}
