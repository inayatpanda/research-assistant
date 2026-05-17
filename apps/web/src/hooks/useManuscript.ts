import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'

import { type ManuscriptSectionName, manuscriptApi } from '@/lib/api'

/**
 * Manuscript section state + autosave (1200ms debounce).
 * Returns the editor-friendly HTML + a setter the editor wires up via onUpdate.
 */
export function useManuscript(
  projectId: string | undefined,
  section: ManuscriptSectionName,
) {
  const qc = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ['manuscript-section', projectId, section],
    queryFn: () => manuscriptApi.getSection(projectId!, section),
    enabled: !!projectId,
  })

  const mutation = useMutation({
    mutationFn: (html: string) => manuscriptApi.upsertSection(projectId!, section, html),
    onSuccess: (saved) =>
      qc.setQueryData(['manuscript-section', projectId, section], saved),
  })

  const [local, setLocal] = useState<string>('')
  const initialised = useRef(false)
  useEffect(() => {
    if (data && !initialised.current) {
      setLocal(htmlOrWrapPlain(data.content))
      initialised.current = true
    }
  }, [data])

  // Reset initialised flag when section changes
  useEffect(() => {
    initialised.current = false
  }, [section, projectId])

  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)
  useEffect(() => {
    if (!initialised.current || !projectId) return
    if (timer.current) clearTimeout(timer.current)
    timer.current = setTimeout(() => mutation.mutate(local), 1200)
    return () => {
      if (timer.current) clearTimeout(timer.current)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [local, projectId, section])

  return {
    html: local,
    setHtml: setLocal,
    saving: mutation.isPending,
    savedAt: data?.updated_at ?? null,
    wordCount: data?.word_count ?? 0,
    loading: isLoading,
  }
}

/** Phase 4 stored plain text. If we see content that isn't HTML, wrap in <p>.  */
function htmlOrWrapPlain(content: string): string {
  if (!content) return ''
  const trimmed = content.trimStart()
  if (trimmed.startsWith('<')) return content
  return `<p>${content.replace(/\n\n+/g, '</p><p>').replace(/\n/g, '<br>')}</p>`
}
