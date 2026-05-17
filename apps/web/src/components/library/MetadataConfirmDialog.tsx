import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { toast } from 'sonner'
import { z } from 'zod'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { articlesApi, type Article } from '@/lib/api'

const FormSchema = z.object({
  title: z.string().min(1).max(1000),
  authors: z.string(),  // comma-separated; transformed on submit
  journal: z.string(),
  year: z.string(),     // allow empty, parse to number on submit
  volume: z.string(),
  issue: z.string(),
  pages: z.string(),
  doi: z.string(),
  study_design: z.string(),
})

type FormValues = z.infer<typeof FormSchema>

const STUDY_DESIGNS = [
  'unspecified',
  'RCT',
  'cohort',
  'case-control',
  'case-series',
  'cross-sectional',
  'systematic-review',
  'meta-analysis',
  'narrative-review',
  'in-vitro',
  'animal',
] as const

function asListOrNull(s: string): string[] | null {
  const arr = s
    .split(',')
    .map((x) => x.trim())
    .filter(Boolean)
  return arr.length ? arr : null
}

function emptyToNull(s: string): string | null {
  const t = s.trim()
  return t.length ? t : null
}

function asYearOrNull(s: string): number | null {
  const n = parseInt(s, 10)
  return Number.isFinite(n) && n >= 1500 && n <= 2200 ? n : null
}

export function MetadataConfirmDialog({
  article,
  open,
  onOpenChange,
}: {
  article: Article | null
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const qc = useQueryClient()

  const form = useForm<FormValues>({
    resolver: zodResolver(FormSchema),
    defaultValues: {
      title: '',
      authors: '',
      journal: '',
      year: '',
      volume: '',
      issue: '',
      pages: '',
      doi: '',
      study_design: 'unspecified',
    },
  })

  // Reset form when a new article opens
  useEffect(() => {
    if (article) {
      form.reset({
        title: article.title,
        authors: article.authors.join(', '),
        journal: article.journal ?? '',
        year: article.year ? String(article.year) : '',
        volume: article.volume ?? '',
        issue: article.issue ?? '',
        pages: article.pages ?? '',
        doi: article.doi ?? '',
        study_design: article.study_design ?? 'unspecified',
      })
    }
  }, [article, form])

  const save = useMutation({
    mutationFn: (values: FormValues) => {
      if (!article) throw new Error('No article in flight')
      return articlesApi.update(article.id, {
        title: values.title.trim(),
        authors: asListOrNull(values.authors) ?? [],
        journal: emptyToNull(values.journal),
        year: asYearOrNull(values.year),
        volume: emptyToNull(values.volume),
        issue: emptyToNull(values.issue),
        pages: emptyToNull(values.pages),
        doi: emptyToNull(values.doi),
        study_design: values.study_design === 'unspecified' ? null : values.study_design,
      })
    },
    onSuccess: (updated) => {
      qc.invalidateQueries({ queryKey: ['articles', updated.project_id] })
      toast.success('Saved')
      onOpenChange(false)
    },
    onError: (e: Error) => toast.error(e.message),
  })

  if (!article) return null

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[640px] max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            Confirm metadata
            {typeof article.year === 'number' && (
              <Badge variant="secondary" className="text-[10px]">
                AI-extracted
              </Badge>
            )}
          </DialogTitle>
          <DialogDescription>
            Review what was extracted from the PDF and edit anything that's wrong before saving.
          </DialogDescription>
        </DialogHeader>

        <form
          onSubmit={form.handleSubmit((v) => save.mutate(v))}
          className="space-y-3 pt-2"
        >
          <Field label="Title" required>
            <Input {...form.register('title')} />
          </Field>
          <Field label="Authors (comma-separated)">
            <Input {...form.register('authors')} placeholder="Jane Doe, John Smith" />
          </Field>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Journal">
              <Input {...form.register('journal')} />
            </Field>
            <Field label="Year">
              <Input type="number" {...form.register('year')} />
            </Field>
          </div>
          <div className="grid grid-cols-3 gap-3">
            <Field label="Volume">
              <Input {...form.register('volume')} />
            </Field>
            <Field label="Issue">
              <Input {...form.register('issue')} />
            </Field>
            <Field label="Pages">
              <Input {...form.register('pages')} placeholder="100-110" />
            </Field>
          </div>
          <Field label="DOI">
            <Input {...form.register('doi')} placeholder="10.1234/example" />
          </Field>
          <Field label="Study design">
            <Select
              value={form.watch('study_design')}
              onValueChange={(v) => form.setValue('study_design', v)}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {STUDY_DESIGNS.map((d) => (
                  <SelectItem key={d} value={d}>
                    {d}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </Field>

          <DialogFooter className="pt-3">
            <Button type="button" variant="ghost" onClick={() => onOpenChange(false)}>
              Edit later
            </Button>
            <Button
              type="submit"
              disabled={save.isPending}
              className="bg-accent hover:bg-accent-hover text-white"
            >
              {save.isPending ? 'Saving…' : 'Save'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

function Field({
  label,
  children,
  required,
}: {
  label: string
  children: React.ReactNode
  required?: boolean
}) {
  return (
    <div className="space-y-1.5">
      <Label className="text-[13px]">
        {label}
        {required && <span className="text-rose-500"> *</span>}
      </Label>
      {children}
    </div>
  )
}
