import { formatDistanceToNow } from 'date-fns'

export function WordCountBar({
  sectionWords,
  totalWords,
  saving,
  savedAt,
}: {
  sectionWords: number
  totalWords: number
  saving: boolean
  savedAt: string | null
}) {
  return (
    <div className="border-t border-border bg-white px-5 py-2 flex items-center justify-between text-[11px] text-muted-foreground">
      <div className="flex items-center gap-3">
        <span><span className="font-medium text-foreground">{sectionWords}</span> words in this section</span>
        <span>·</span>
        <span><span className="font-medium text-foreground">{totalWords}</span> total</span>
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
