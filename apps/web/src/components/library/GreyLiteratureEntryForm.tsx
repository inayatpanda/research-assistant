/**
 * Phase 16 (MP16) — Manual entry form for grey-literature references.
 *
 * Covers the cases where an authoritative identifier (DOI/PMID) doesn't
 * exist or doesn't resolve, e.g. URL-only web pages, theses, preprints,
 * registry records (ClinicalTrials.gov), conference abstracts, books.
 *
 * The submitted payload is shaped as ``ArticleMetadata`` so it can flow
 * through the existing ``importFromMetadata`` route alongside DOI / PubMed
 * imports.
 */
import { useState } from 'react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import type { ReferenceType } from '@/lib/api'

const REFERENCE_TYPE_LABELS: Array<{ value: ReferenceType; label: string }> = [
  { value: 'web_resource', label: 'Web resource' },
  { value: 'thesis', label: 'Thesis / dissertation' },
  { value: 'preprint', label: 'Preprint' },
  { value: 'registry_record', label: 'Trial registry record' },
  { value: 'report', label: 'Technical report' },
  { value: 'book', label: 'Book' },
  { value: 'book_chapter', label: 'Book chapter' },
  { value: 'conference_abstract', label: 'Conference abstract' },
  { value: 'other', label: 'Other' },
]

export interface GreyLiteratureFormValue {
  title: string
  authors: string[]
  year: number | null
  journal: string | null
  url: string | null
  doi: string | null
  reference_type: ReferenceType
}

export function GreyLiteratureEntryForm({
  onSubmit,
  busy,
  defaultReferenceType = 'web_resource',
}: {
  onSubmit: (value: GreyLiteratureFormValue) => void | Promise<void>
  busy?: boolean
  defaultReferenceType?: ReferenceType
}) {
  const [title, setTitle] = useState('')
  const [authorsText, setAuthorsText] = useState('')
  const [year, setYear] = useState('')
  const [journal, setJournal] = useState('')
  const [url, setUrl] = useState('')
  const [doi, setDoi] = useState('')
  const [referenceType, setReferenceType] =
    useState<ReferenceType>(defaultReferenceType)

  function buildValue(): GreyLiteratureFormValue | null {
    if (!title.trim()) {
      toast.error('Title is required')
      return null
    }
    const authors = authorsText
      .split(/\n|;/)
      .map((s) => s.trim())
      .filter(Boolean)
    const yearNum = year.trim() ? Number(year.trim()) : null
    if (year.trim() && (Number.isNaN(yearNum!) || yearNum! < 1500 || yearNum! > 2200)) {
      toast.error('Year must be between 1500 and 2200')
      return null
    }
    return {
      title: title.trim(),
      authors,
      year: yearNum,
      journal: journal.trim() || null,
      url: url.trim() || null,
      doi: doi.trim() || null,
      reference_type: referenceType,
    }
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const v = buildValue()
    if (v) onSubmit(v)
  }

  // Per-type prompt for the `journal` field (which doubles as
  // publisher / university / registry / preprint-server depending on
  // the reference type).
  const journalLabel = (() => {
    switch (referenceType) {
      case 'thesis':
        return 'University'
      case 'preprint':
        return 'Preprint server'
      case 'registry_record':
        return 'Registry'
      case 'book':
      case 'book_chapter':
        return 'Publisher'
      case 'web_resource':
        return 'Organisation (optional)'
      default:
        return 'Source (optional)'
    }
  })()

  return (
    <form onSubmit={handleSubmit} className="space-y-3" aria-label="Grey literature entry">
      <div className="space-y-1.5">
        <Label htmlFor="grey-ref-type">Reference type</Label>
        <Select
          value={referenceType}
          onValueChange={(v) => setReferenceType(v as ReferenceType)}
        >
          <SelectTrigger id="grey-ref-type" aria-label="Reference type">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {REFERENCE_TYPE_LABELS.map((opt) => (
              <SelectItem key={opt.value} value={opt.value}>
                {opt.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="grey-title">Title</Label>
        <Input
          id="grey-title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Title"
          required
        />
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1.5">
          <Label htmlFor="grey-authors">Authors (one per line)</Label>
          <textarea
            id="grey-authors"
            value={authorsText}
            onChange={(e) => setAuthorsText(e.target.value)}
            className="w-full min-h-[80px] rounded-md border border-border bg-white px-3 py-2 text-[12px]"
            placeholder={'Jane Doe\nJohn Smith'}
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="grey-year">Year</Label>
          <Input
            id="grey-year"
            value={year}
            onChange={(e) => setYear(e.target.value)}
            placeholder="2024"
            inputMode="numeric"
          />
        </div>
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="grey-journal">{journalLabel}</Label>
        <Input
          id="grey-journal"
          value={journal}
          onChange={(e) => setJournal(e.target.value)}
        />
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="grey-url">URL</Label>
        <Input
          id="grey-url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://"
          type="url"
        />
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="grey-doi">DOI (optional)</Label>
        <Input
          id="grey-doi"
          value={doi}
          onChange={(e) => setDoi(e.target.value)}
          placeholder="10.xxxx/..."
        />
      </div>

      <Button type="submit" disabled={busy || !title.trim()} className="w-full">
        {busy ? 'Adding…' : 'Add reference'}
      </Button>
    </form>
  )
}
