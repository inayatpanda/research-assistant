import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'

import { notesApi } from '@/lib/api'

/** Article notes hook with 700ms debounced autosave. */
export function useArticleNote(articleId: string | undefined) {
  const qc = useQueryClient()

  const query = useQuery({
    queryKey: ['note', articleId],
    queryFn: () => notesApi.get(articleId!),
    enabled: !!articleId,
  })

  const mutation = useMutation({
    mutationFn: (content: string) => notesApi.upsert(articleId!, content),
    onSuccess: (saved) => qc.setQueryData(['note', articleId], saved),
  })

  const [local, setLocal] = useState<string>('')
  const initialised = useRef(false)
  useEffect(() => {
    if (query.data && !initialised.current) {
      setLocal(query.data.content)
      initialised.current = true
    }
  }, [query.data])

  // Debounced save
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)
  useEffect(() => {
    if (!initialised.current || !articleId) return
    if (timer.current) clearTimeout(timer.current)
    timer.current = setTimeout(() => mutation.mutate(local), 700)
    return () => {
      if (timer.current) clearTimeout(timer.current)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [local, articleId])

  return {
    value: local,
    setValue: setLocal,
    saving: mutation.isPending,
    savedAt: query.data?.updated_at ?? null,
    loading: query.isLoading,
  }
}
