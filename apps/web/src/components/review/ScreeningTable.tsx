import { useQuery } from '@tanstack/react-query'
import { useMemo } from 'react'

import {
  articlesApi,
  type Article,
  type ReviewStage,
  type ScreeningRecord,
} from '@/lib/api'
import { useScreening } from '@/hooks/useReviews'

import { ScreeningRowActions } from './ScreeningRowActions'

export function ScreeningTable({
  projectId,
  stage,
}: {
  projectId: string
  stage: ReviewStage
}) {
  const { data: articles = [], isLoading: aLoading } = useQuery({
    queryKey: ['articles', projectId, { sort: 'created_desc' }],
    queryFn: () => articlesApi.list(projectId, { sort: 'created_desc' }),
  })

  // Always fetch *all* screening records so we can compute which articles
  // qualify for the full-text stage (those marked include/maybe in
  // title_abstract).
  const { data: allScreening = [], isLoading: sLoading } = useScreening(
    projectId,
    undefined,
  )

  const byArticleAndStage = useMemo(() => {
    const map = new Map<string, Map<ReviewStage, ScreeningRecord>>()
    for (const r of allScreening) {
      const inner = map.get(r.article_id) ?? new Map()
      inner.set(r.stage as ReviewStage, r)
      map.set(r.article_id, inner)
    }
    return map
  }, [allScreening])

  const visibleArticles = useMemo(() => {
    if (stage === 'title_abstract') return articles
    return articles.filter((a) => {
      const ta = byArticleAndStage.get(a.id)?.get('title_abstract')
      return ta && (ta.decision === 'include' || ta.decision === 'maybe')
    })
  }, [articles, stage, byArticleAndStage])

  const loading = aLoading || sLoading

  return (
    <div className="rounded-lg border border-border bg-white overflow-hidden">
      <div className="px-4 py-2.5 border-b border-border bg-muted/30 text-[11px] uppercase tracking-wider text-muted-foreground font-medium flex items-center justify-between">
        <span>
          {stage === 'title_abstract' ? 'Title / Abstract screening' : 'Full-text screening'}
        </span>
        <span>{visibleArticles.length} article{visibleArticles.length === 1 ? '' : 's'}</span>
      </div>

      {loading ? (
        <div className="px-4 py-8 text-center text-[13px] text-muted-foreground">
          Loading…
        </div>
      ) : visibleArticles.length === 0 ? (
        <div className="px-4 py-10 text-center text-[13px] text-muted-foreground">
          {stage === 'title_abstract'
            ? 'No articles in this project yet. Add them from the Library tab.'
            : 'No articles passed title/abstract screening yet. Mark articles include or maybe in the Title/Abstract stage to assess them here.'}
        </div>
      ) : (
        <ul className="divide-y divide-border">
          {visibleArticles.map((a) => (
            <ScreeningRow
              key={a.id}
              projectId={projectId}
              article={a}
              stage={stage}
              record={byArticleAndStage.get(a.id)?.get(stage)}
            />
          ))}
        </ul>
      )}
    </div>
  )
}

function ScreeningRow({
  projectId,
  article,
  stage,
  record,
}: {
  projectId: string
  article: Article
  stage: ReviewStage
  record: ScreeningRecord | undefined
}) {
  return (
    <li className="px-4 py-3 flex items-start gap-4">
      <div className="min-w-0 flex-1">
        <div className="text-[13px] font-medium leading-snug">{article.title}</div>
        <div className="mt-0.5 text-[11px] text-muted-foreground truncate">
          {article.authors.slice(0, 3).join(', ')}
          {article.authors.length > 3 ? ' et al.' : ''}
          {article.journal ? ` · ${article.journal}` : ''}
          {article.year ? ` · ${article.year}` : ''}
        </div>
        {article.study_design && (
          <div className="mt-1 text-[10px] uppercase tracking-wider text-muted-foreground/80">
            {article.study_design}
          </div>
        )}
      </div>
      <div className="shrink-0">
        <ScreeningRowActions
          projectId={projectId}
          articleId={article.id}
          stage={stage}
          record={record}
        />
      </div>
    </li>
  )
}
