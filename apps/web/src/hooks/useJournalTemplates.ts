import { useQuery } from '@tanstack/react-query'

import { journalTemplatesApi, type JournalTemplate } from '@/lib/api'

export function useJournalTemplates() {
  return useQuery<JournalTemplate[]>({
    queryKey: ['journal-templates'],
    queryFn: () => journalTemplatesApi.list(),
    staleTime: 60 * 60 * 1000,
  })
}

/** Find a template by key from the cached list. Returns null if not yet loaded
 *  or the key isn't in the catalogue. */
export function useJournalTemplate(key: string | null | undefined): JournalTemplate | null {
  const { data } = useJournalTemplates()
  if (!key || !data) return null
  return data.find((t) => t.key === key) ?? null
}
