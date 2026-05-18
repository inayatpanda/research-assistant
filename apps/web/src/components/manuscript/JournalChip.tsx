import { BookOpen } from 'lucide-react'
import { Link } from 'react-router-dom'

import { useJournalTemplate } from '@/hooks/useJournalTemplates'

export function JournalChip({
  templateKey,
}: {
  templateKey: string | null | undefined
}) {
  const template = useJournalTemplate(templateKey)

  if (!templateKey) {
    return (
      <Link
        to="/settings"
        className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-zinc-100 text-zinc-700 hover:bg-zinc-200"
        aria-label="Select a journal template"
      >
        <BookOpen className="w-3 h-3" /> No template — pick one
      </Link>
    )
  }

  if (!template) {
    return (
      <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-zinc-100 text-zinc-700">
        <BookOpen className="w-3 h-3" /> {templateKey}
      </span>
    )
  }

  return (
    <Link
      to="/settings"
      title="Change journal template in Settings"
      className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-blue-50 text-blue-800 hover:bg-blue-100"
    >
      <BookOpen className="w-3 h-3" />
      Targeting: {template.label.split(' ')[0]} · max {template.max_total_words} words
    </Link>
  )
}
