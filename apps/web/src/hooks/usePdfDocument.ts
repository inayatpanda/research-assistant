import { useQuery } from '@tanstack/react-query'
import { del, get, set } from 'idb-keyval'

import { absoluteFileUrl, articlesApi } from '@/lib/api'

/** Fetches the PDF bytes for an article, caching in IndexedDB so re-opening is instant.
 *  Signed URLs expire after 1h; cached bytes survive that and we just re-fetch on miss.
 */
export function usePdfDocument(articleId: string | undefined) {
  return useQuery({
    queryKey: ['pdf', articleId],
    enabled: !!articleId,
    queryFn: async (): Promise<{ data: ArrayBuffer; fileType: string }> => {
      const cacheKey = `pdf:${articleId}`
      const cached = await get<{ data: ArrayBuffer; fileType: string }>(cacheKey)
      if (cached) return cached

      const article = await articlesApi.get(articleId!)
      const url = absoluteFileUrl(article.file_url ?? null)
      if (!url) throw new Error('Article has no file attached')
      const res = await fetch(url)
      if (!res.ok) throw new Error(`Failed to download PDF (HTTP ${res.status})`)
      const buf = await res.arrayBuffer()
      const value = { data: buf, fileType: article.file_type ?? 'application/pdf' }
      await set(cacheKey, value)
      return value
    },
    staleTime: Infinity, // Cache forever — bytes never change for a saved article
  })
}

export async function clearPdfCache(articleId: string): Promise<void> {
  await del(`pdf:${articleId}`)
}
