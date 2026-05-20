/**
 * Phase 12 — Cover-letter editor.
 *
 * Surface:
 *   - Journal selector (from the journal templates catalogue).
 *   - Novelty bullets (add / remove inline).
 *   - "Draft with AI" button — calls POST /draft, replaces body_html.
 *   - HTML body editor (textarea — TipTap not used to keep this simple,
 *     researchers paste-revise the AI's prose).
 *   - "Save" button — PATCHes target_journal / novelty / body_html.
 */
import { useEffect, useState } from 'react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import {
  useCoverLetter,
  useDraftCoverLetter,
  useUpdateCoverLetter,
} from '@/hooks/useCoverLetter'
import { useJournalTemplates } from '@/hooks/useJournalTemplates'
import { coverLetterApi } from '@/lib/api'

const NONE_VALUE = '__none__'

export function CoverLetterEditor({ projectId }: { projectId: string }) {
  const { data, isLoading } = useCoverLetter(projectId)
  const update = useUpdateCoverLetter(projectId)
  const draft = useDraftCoverLetter(projectId)
  const { data: journals = [] } = useJournalTemplates()

  const [journal, setJournal] = useState<string | null>(null)
  const [novelty, setNovelty] = useState<string[]>([])
  const [body, setBody] = useState('')
  const [newBullet, setNewBullet] = useState('')
  const [downloading, setDownloading] = useState(false)

  // Hydrate state once the server data lands.
  useEffect(() => {
    if (!data) return
    setJournal(data.target_journal ?? null)
    setNovelty(data.novelty_points ?? [])
    setBody(data.body_html ?? '')
  }, [data])

  if (isLoading) {
    return (
      <div className="text-sm text-muted-foreground">Loading cover letter…</div>
    )
  }

  function addBullet() {
    const trimmed = newBullet.trim()
    if (!trimmed) return
    if (novelty.length >= 12) {
      toast.error('Up to 12 novelty bullets')
      return
    }
    setNovelty([...novelty, trimmed])
    setNewBullet('')
  }

  function removeBullet(idx: number) {
    setNovelty(novelty.filter((_, i) => i !== idx))
  }

  async function handleSave() {
    try {
      await update.mutateAsync({
        target_journal: journal,
        novelty_points: novelty,
        body_html: body,
      })
      toast.success('Cover letter saved')
    } catch (e) {
      toast.error((e as Error).message || 'Could not save cover letter')
    }
  }

  async function handleDownload() {
    if (!body.trim()) {
      toast.error('Draft or paste the letter body first')
      return
    }
    setDownloading(true)
    try {
      const filename = await coverLetterApi.downloadDocx(projectId)
      toast.success(`Downloaded ${filename}`)
    } catch (e) {
      const msg = (e as Error).message || ''
      if (/422/.test(msg)) toast.error('Cover letter is empty')
      else toast.error(msg || 'Could not download DOCX')
    } finally {
      setDownloading(false)
    }
  }

  async function handleDraft() {
    if (!journal) {
      toast.error('Pick a target journal first')
      return
    }
    try {
      const fresh = await draft.mutateAsync({
        target_journal: journal,
        novelty_points: novelty,
      })
      setBody(fresh.body_html)
      toast.success('Cover letter drafted')
    } catch (e) {
      const msg = (e as Error).message || ''
      if (/503/.test(msg)) {
        toast.error('AI provider unavailable — check your key')
      } else if (/429/.test(msg)) {
        toast.error('AI rate limited — try again shortly')
      } else {
        toast.error(msg || 'Could not draft cover letter')
      }
    }
  }

  return (
    <Card data-testid="cover-letter-editor">
      <CardHeader>
        <CardTitle>Cover letter</CardTitle>
        <CardDescription>
          Target journal, novelty bullets, and the editable letter body.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-1">
          <Label htmlFor="cover-journal">Target journal</Label>
          <Select
            value={journal ?? NONE_VALUE}
            onValueChange={(v) => setJournal(v === NONE_VALUE ? null : v)}
          >
            <SelectTrigger
              id="cover-journal"
              data-testid="cover-journal-trigger"
              className="w-full max-w-md"
            >
              <SelectValue placeholder="— pick a journal —" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={NONE_VALUE}>— None —</SelectItem>
              {journals.map((j) => (
                <SelectItem key={j.key} value={j.key}>
                  {j.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-1">
          <Label>Novelty bullets</Label>
          <ul className="space-y-1" data-testid="cover-novelty-list">
            {novelty.map((b, idx) => (
              <li
                key={`${idx}-${b}`}
                className="flex items-center gap-2 rounded border border-border bg-white px-2 py-1 text-sm"
              >
                <span className="flex-1">{b}</span>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 px-2 text-rose-600"
                  onClick={() => removeBullet(idx)}
                  data-testid={`cover-novelty-remove-${idx}`}
                >
                  Remove
                </Button>
              </li>
            ))}
          </ul>
          <div className="flex gap-2">
            <Input
              value={newBullet}
              placeholder="Add a novelty bullet…"
              onChange={(e) => setNewBullet(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault()
                  addBullet()
                }
              }}
              data-testid="cover-novelty-input"
            />
            <Button
              variant="outline"
              onClick={addBullet}
              data-testid="cover-novelty-add"
            >
              Add
            </Button>
          </div>
        </div>

        <div className="space-y-1">
          <div className="flex items-center justify-between">
            <Label htmlFor="cover-body">Letter body (HTML)</Label>
            <Button
              size="sm"
              variant="secondary"
              disabled={draft.isPending || !journal}
              onClick={handleDraft}
              data-testid="cover-draft-button"
            >
              {draft.isPending ? 'Drafting…' : 'Draft with AI'}
            </Button>
          </div>
          <Textarea
            id="cover-body"
            value={body}
            rows={14}
            placeholder="<p>Dear Editor,</p>…"
            onChange={(e) => setBody(e.target.value)}
            data-testid="cover-body-input"
          />
        </div>

        <div className="flex justify-end gap-2">
          <Button
            variant="outline"
            onClick={handleDownload}
            disabled={downloading || !body.trim()}
            data-testid="cover-download-button"
          >
            {downloading ? 'Downloading…' : 'Download DOCX'}
          </Button>
          <Button
            onClick={handleSave}
            disabled={update.isPending}
            data-testid="cover-save-button"
          >
            {update.isPending ? 'Saving…' : 'Save cover letter'}
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
