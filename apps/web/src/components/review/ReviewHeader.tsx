import { Loader2, Pencil } from 'lucide-react'
import { useEffect, useState } from 'react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import {
  Sheet,
  SheetContent,
  SheetTrigger,
} from '@/components/ui/sheet'
import { Textarea } from '@/components/ui/textarea'
import { type Review } from '@/lib/api'
import { useReview, useUpdateReview } from '@/hooks/useReviews'

const FIELDS: Array<{
  key: keyof Review
  label: string
  placeholder: string
  rows?: number
}> = [
  {
    key: 'pico_population',
    label: 'Population',
    placeholder: 'e.g. adults undergoing total knee arthroplasty',
  },
  {
    key: 'pico_intervention',
    label: 'Intervention',
    placeholder: 'e.g. tranexamic acid (any route)',
  },
  {
    key: 'pico_comparator',
    label: 'Comparator',
    placeholder: 'e.g. placebo or standard care',
  },
  {
    key: 'pico_outcome',
    label: 'Outcome',
    placeholder: 'e.g. transfusion rate, blood loss',
  },
  {
    key: 'eligibility_inclusion',
    label: 'Inclusion criteria',
    placeholder: 'One per line',
    rows: 4,
  },
  {
    key: 'eligibility_exclusion',
    label: 'Exclusion criteria',
    placeholder: 'One per line',
    rows: 4,
  },
]

export function ReviewHeader({ projectId }: { projectId: string }) {
  const { data: review, isLoading } = useReview(projectId)
  const [open, setOpen] = useState(false)

  if (isLoading || !review) {
    return (
      <div className="rounded-lg border border-border bg-white/60 p-5 animate-pulse">
        <div className="h-3 w-24 bg-muted rounded" />
        <div className="mt-3 h-4 w-3/4 bg-muted rounded" />
      </div>
    )
  }

  return (
    <div className="rounded-lg border border-border bg-white p-5">
      <header className="flex items-center justify-between gap-3">
        <div>
          <div className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
            PICO & Eligibility
          </div>
          <div className="mt-0.5 text-[13px] text-muted-foreground">
            Used as the question framework for screening and extraction.
          </div>
        </div>
        <Sheet open={open} onOpenChange={setOpen}>
          <SheetTrigger asChild>
            <Button variant="outline" size="sm" className="h-8 text-[12px]">
              <Pencil className="h-3.5 w-3.5 mr-1.5" />
              Edit
            </Button>
          </SheetTrigger>
          <SheetContent side="right" className="w-[480px] sm:max-w-[480px] overflow-y-auto">
            <ReviewEditPanel
              projectId={projectId}
              review={review}
              onDone={() => setOpen(false)}
            />
          </SheetContent>
        </Sheet>
      </header>

      <dl className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-3">
        {FIELDS.map((f) => (
          <div key={f.key} className="rounded-md border border-border/70 bg-muted/20 px-3 py-2">
            <dt className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium">
              {f.label}
            </dt>
            <dd className="mt-0.5 text-[13px] whitespace-pre-wrap">
              {(review[f.key] as string | null) || (
                <span className="text-muted-foreground/70 italic">Not set</span>
              )}
            </dd>
          </div>
        ))}
      </dl>
    </div>
  )
}

function ReviewEditPanel({
  projectId,
  review,
  onDone,
}: {
  projectId: string
  review: Review
  onDone: () => void
}) {
  const update = useUpdateReview(projectId)
  const [draft, setDraft] = useState<Record<string, string>>(() => {
    const out: Record<string, string> = {}
    for (const f of FIELDS) out[f.key] = (review[f.key] as string | null) ?? ''
    return out
  })

  useEffect(() => {
    const out: Record<string, string> = {}
    for (const f of FIELDS) out[f.key] = (review[f.key] as string | null) ?? ''
    setDraft(out)
  }, [review])

  function save() {
    const body: Record<string, string | null> = {}
    for (const f of FIELDS) {
      const v = (draft[f.key] ?? '').trim()
      body[f.key] = v.length ? v : null
    }
    update.mutate(body, {
      onSuccess: () => {
        toast.success('Review updated')
        onDone()
      },
      onError: (e: Error) => toast.error(e.message),
    })
  }

  return (
    <div className="space-y-4 pt-4">
      <div>
        <div className="text-[15px] font-semibold tracking-tight">
          Edit PICO & eligibility
        </div>
        <div className="text-[12px] text-muted-foreground mt-1">
          These fields drive AI screening suggestions and the manuscript's Methodology section.
        </div>
      </div>
      <div className="space-y-3">
        {FIELDS.map((f) => (
          <label key={f.key} className="block space-y-1">
            <span className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
              {f.label}
            </span>
            <Textarea
              value={draft[f.key]}
              onChange={(e) =>
                setDraft((d) => ({ ...d, [f.key]: e.target.value }))
              }
              placeholder={f.placeholder}
              rows={f.rows ?? 2}
            />
          </label>
        ))}
      </div>
      <div className="flex justify-end gap-2 pt-2">
        <Button variant="ghost" size="sm" onClick={onDone}>
          Cancel
        </Button>
        <Button
          size="sm"
          onClick={save}
          disabled={update.isPending}
          className="bg-accent hover:bg-accent-hover text-white"
        >
          {update.isPending && <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />}
          Save
        </Button>
      </div>
    </div>
  )
}
