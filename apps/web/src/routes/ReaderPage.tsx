import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, FileText } from 'lucide-react'
import { Link, useParams, useSearchParams } from 'react-router-dom'

import { ReaderShell } from '@/components/reader/ReaderShell'
import { Skeleton } from '@/components/ui/skeleton'
import { articlesApi } from '@/lib/api'
import { useProjectId } from '@/lib/projectContext'

export default function ReaderPage() {
  const projectId = useProjectId()
  const { articleId: paramArticleId } = useParams<{ articleId: string }>()
  const [searchParams] = useSearchParams()
  // Accept `?article=<id>` as a fallback alongside the path-param route so
  // external links / share URLs don't have to know about the segment layout.
  const articleId = paramArticleId ?? searchParams.get('article') ?? undefined
  const libraryHref = `/projects/${projectId}/library`

  const { data: article, isLoading, isError } = useQuery({
    queryKey: ['article', articleId],
    queryFn: () => articlesApi.get(articleId!),
    enabled: !!articleId,
  })

  if (!articleId) {
    return (
      <div className="max-w-2xl mx-auto px-8 py-16 text-center">
        <FileText className="h-8 w-8 mx-auto text-muted-foreground" />
        <h2 className="mt-4 text-[20px] font-semibold tracking-tight">Pick an article</h2>
        <p className="mt-2 text-[14px] text-muted-foreground">
          The Reader opens individual articles. Pick one from the Library.
        </p>
        <Link
          to={libraryHref}
          className="mt-6 inline-flex items-center gap-1.5 text-[13px] text-accent hover:underline"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Go to Library
        </Link>
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="p-8 space-y-4">
        <Skeleton className="h-8 w-1/2" />
        <Skeleton className="h-[600px] w-full" />
      </div>
    )
  }

  if (isError || !article) {
    return (
      <div className="max-w-2xl mx-auto px-8 py-16 text-center">
        <h2 className="text-[18px] font-semibold tracking-tight text-rose-700">Article not found</h2>
        <Link
          to={libraryHref}
          className="mt-4 inline-flex items-center gap-1.5 text-[13px] text-accent hover:underline"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Back to Library
        </Link>
      </div>
    )
  }

  return <ReaderShell article={article} />
}
