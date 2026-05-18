import { formatDistanceToNow } from 'date-fns'

import { useJournalTemplate } from '@/hooks/useJournalTemplates'

function ratioClass(words: number, cap: number | null): string {
  if (!cap || cap <= 0) return 'text-foreground'
  const ratio = words / cap
  if (ratio >= 1.0) return 'text-red-600 font-semibold'
  if (ratio >= 0.9) return 'text-amber-600 font-semibold'
  return 'text-foreground'
}

export function WordCountBar({
  sectionWords,
  totalWords,
  saving,
  savedAt,
  templateKey,
  activeSectionName,
}: {
  sectionWords: number
  totalWords: number
  saving: boolean
  savedAt: string | null
  templateKey?: string | null
  activeSectionName?: string
}) {
  const template = useJournalTemplate(templateKey ?? null)
  const sectionCap =
    template && activeSectionName ? template.max_words_by_section[activeSectionName] ?? null : null
  const totalCap = template?.max_total_words ?? null

  return (
    <div
      className="border-t border-border bg-white px-5 py-2 flex items-center justify-between text-[11px] text-muted-foreground"
      data-testid="word-count-bar"
    >
      <div className="flex items-center gap-3">
        <span>
          <span className={`font-medium ${ratioClass(sectionWords, sectionCap)}`}>
            {sectionWords}
          </span>{' '}
          {sectionCap ? `/ ${sectionCap}` : ''} words in this section
        </span>
        <span>·</span>
        <span>
          <span className={`font-medium ${ratioClass(totalWords, totalCap)}`}>
            {totalWords}
          </span>{' '}
          {totalCap ? `/ ${totalCap}` : ''} total
        </span>
      </div>
      <div>
        {saving
          ? 'Saving…'
          : savedAt
            ? `Saved ${formatDistanceToNow(new Date(savedAt))} ago`
            : 'Autosave on'}
      </div>
    </div>
  )
}
