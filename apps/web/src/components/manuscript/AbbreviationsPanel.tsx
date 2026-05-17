import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Save } from 'lucide-react'
import { useMemo } from 'react'
import { toast } from 'sonner'

import { abbreviationsApi, manuscriptApi, type ManuscriptSectionName } from '@/lib/api'
import { Button } from '@/components/ui/button'

const SECTIONS: ManuscriptSectionName[] = [
  'Abstract',
  'Introduction',
  'Methodology',
  'Results',
  'Discussion',
  'Conclusion',
]

const ABBR_RE = /\(([A-Z][A-Za-z]{1,9}s?)\)/g

/** Mirror of services/abbreviation_scanner.py — kept client-side for live preview. */
function scanAbbreviations(text: string): Array<{ short_form: string; long_form: string }> {
  const found = new Map<string, string>()
  let m: RegExpExecArray | null
  ABBR_RE.lastIndex = 0
  while ((m = ABBR_RE.exec(text))) {
    const abbr = m[1]
    const upperLetters = abbr.replace(/[^A-Z]/g, '')
    if (upperLetters.length < 2) continue
    const before = text.slice(0, m.index).trimEnd()
    const words = before.match(/[A-Za-z][A-Za-z-]*/g)
    if (!words || words.length < upperLetters.length) continue
    const tail = words.slice(-upperLetters.length)
    const initials = tail.map((w) => w[0].toUpperCase()).join('')
    if (initials !== upperLetters) continue
    if (!found.has(abbr)) found.set(abbr, tail.join(' '))
  }
  return Array.from(found.entries()).map(([short_form, long_form]) => ({ short_form, long_form }))
}

function htmlToText(html: string): string {
  if (!html) return ''
  const div = document.createElement('div')
  div.innerHTML = html
  return div.textContent ?? ''
}

export function AbbreviationsPanel({ projectId }: { projectId: string }) {
  const qc = useQueryClient()
  const { data: saved = [] } = useQuery({
    queryKey: ['abbreviations', projectId],
    queryFn: () => abbreviationsApi.list(projectId),
  })

  const sectionQueries = SECTIONS.map((s) =>
    useQuery({
      queryKey: ['manuscript-section', projectId, s],
      queryFn: () => manuscriptApi.getSection(projectId, s),
    }),
  )

  const detected = useMemo(() => {
    const fullText = SECTIONS.map((_, i) =>
      htmlToText(sectionQueries[i].data?.content ?? ''),
    ).join('\n')
    return scanAbbreviations(fullText)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sectionQueries.map((q) => q.data?.content).join('|')])

  const save = useMutation({
    mutationFn: () => abbreviationsApi.replace(projectId, detected),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['abbreviations', projectId] })
      toast.success('Abbreviations saved')
    },
    onError: (e: Error) => toast.error(e.message),
  })

  const dirty = useMemo(() => {
    const savedSet = new Map(saved.map((a) => [a.short_form, a.long_form]))
    if (savedSet.size !== detected.length) return true
    return detected.some((d) => savedSet.get(d.short_form) !== d.long_form)
  }, [saved, detected])

  return (
    <div className="rounded-md border border-border bg-white p-4 space-y-3">
      <div className="flex items-center justify-between gap-2">
        <div className="text-[13px] font-semibold tracking-tight">Abbreviations</div>
        <Button
          size="sm"
          variant="outline"
          disabled={!dirty || save.isPending}
          onClick={() => save.mutate()}
          className="h-7 text-[11px]"
        >
          <Save className="h-3 w-3 mr-1" />
          {save.isPending ? 'Saving…' : dirty ? 'Save' : 'Up to date'}
        </Button>
      </div>
      <div className="text-[12px] text-muted-foreground">
        Detected from manuscript text:
      </div>
      {detected.length === 0 ? (
        <div className="text-[12px] text-muted-foreground italic">
          None yet. Write a phrase like “Total hip arthroplasty (THA)” to register one.
        </div>
      ) : (
        <ul className="space-y-1 text-[12px]">
          {detected.map((a) => (
            <li key={a.short_form} className="flex gap-2">
              <span className="font-mono font-semibold w-12 shrink-0">{a.short_form}</span>
              <span className="text-muted-foreground">{a.long_form}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
