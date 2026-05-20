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
    onSuccess: (saved) => {
      qc.setQueryData(['manuscript-section', projectId, section], saved)
      // Citations live inside section content; the bibliography is derived
      // from every section's HTML, so any successful save must re-fetch it.
      // Same for the reference-integrity panel (its useMemo recomputes
      // when section data changes, and the "never cited" list needs to
      // shrink immediately after a new citation is inserted — #A4).
      qc.invalidateQueries({ queryKey: ['bibliography', projectId] })
      qc.invalidateQueries({ queryKey: ['manuscript-section', projectId] })
    },
  })

  const [local, setLocal] = useState<string>('')
  // Server-side content currently observed. Used to:
  //   (a) seed `local` when a fresh section loads,
  //   (b) suppress no-op autosaves (the loaded HTML equals local),
  //   (c) avoid the "initialised flag" race that previously caused
  //       autosave to never fire when the section started empty.
  const serverContent = useRef<string | null>(null)
  useEffect(() => {
    if (!data) return
    const next = htmlOrWrapPlain(data.content)
    if (serverContent.current === next) return
    serverContent.current = next
    setLocal(next)
  }, [data])

  // When the user navigates to a different section, drop the server cache so
  // the next `data` arrival is treated as a fresh load (not as a remote edit
  // we would otherwise clobber over local edits).
  useEffect(() => {
    serverContent.current = null
  }, [section, projectId])

  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)
  useEffect(() => {
    if (!projectId) return
    // Don't autosave until we've seen at least one server response — otherwise
    // a freshly-mounted hook would overwrite the section with the empty
    // initial-state string before the load completes.
    if (serverContent.current === null) return
    // Skip if local equals the last known server value (the load itself sets
    // local; no need to PUT the same content back).
    if (local === serverContent.current) return
    if (timer.current) clearTimeout(timer.current)
    timer.current = setTimeout(() => {
      serverContent.current = local
      mutation.mutate(local)
    }, 1200)
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
