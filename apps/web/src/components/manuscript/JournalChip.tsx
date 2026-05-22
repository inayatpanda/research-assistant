import { BookOpen } from 'lucide-react'
import { Link } from 'react-router-dom'

import { useJournalTemplate } from '@/hooks/useJournalTemplates'

// Fix-E2E/9 — Journal template is a per-project attribute (lives on the
// Project row, not on the global app settings). Deep-link the chip to the
// journal-template card on the global Settings page (where the picker
// actually lives) and make the copy explicit so the user understands the
// indirection. We also expose the chosen template via the URL hash so the
// page can scroll/focus the right card.
const SETTINGS_HREF = '/settings#journal-template'

export function JournalChip({
  templateKey,
}: {
  templateKey: string | null | undefined
}) {
  const template = useJournalTemplate(templateKey)

  if (!templateKey) {
    return (
      <Link
        to={SETTINGS_HREF}
        className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-zinc-100 text-zinc-700 hover:bg-zinc-200"
        aria-label="Pick a journal template in Settings"
        title="Edit in Settings → Journal template"
      >
        <BookOpen className="w-3 h-3" /> No template — pick in Settings
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
      to={SETTINGS_HREF}
      title="Edit in Settings → Journal template"
      className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-blue-50 text-blue-800 hover:bg-blue-100"
    >
      <BookOpen className="w-3 h-3" />
      Targeting: {template.label.split(' ')[0]} · max {template.max_total_words} words
    </Link>
  )
}
