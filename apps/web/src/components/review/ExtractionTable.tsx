import { useQuery } from '@tanstack/react-query'
import { Loader2, Send } from 'lucide-react'
import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import {
  articlesApi,
  type Article,
  type ExtractionField,
  type ExtractionFieldGroup,
  type ExtractionRecord,
  type ScreeningRecord,
} from '@/lib/api'
import {
  useExtractionRecords,
  useExtractionSchema,
  usePushExtraction,
  useScreening,
  useUpdateExtraction,
  useUpsertExtraction,
} from '@/hooks/useReviews'

export function ExtractionTable({ projectId }: { projectId: string }) {
  const navigate = useNavigate()
  const { data: schema = [], isLoading: schemaLoading } = useExtractionSchema(projectId)
  const { data: records = [], isLoading: recLoading } = useExtractionRecords(projectId)
  const { data: screening = [] } = useScreening(projectId, 'full_text')
  const { data: articles = [] } = useQuery({
    queryKey: ['articles', projectId, { sort: 'created_desc' }],
    queryFn: () => articlesApi.list(projectId, { sort: 'created_desc' }),
  })
  const push = usePushExtraction(projectId)

  const includedArticles = useMemo(() => {
    const include = new Set(
      (screening as ScreeningRecord[])
        .filter((s) => s.decision === 'include')
        .map((s) => s.article_id),
    )
    return articles.filter((a) => include.has(a.id))
  }, [articles, screening])

  const recordByArticle = useMemo(() => {
    const m = new Map<string, ExtractionRecord>()
    for (const r of records) m.set(r.article_id, r)
    return m
  }, [records])

  if (schemaLoading || recLoading) {
    return <div className="text-[13px] text-muted-foreground">Loading…</div>
  }

  return (
    <div className="space-y-4">
      <header className="flex items-center justify-between">
        <div>
          <h3 className="text-[15px] font-semibold tracking-tight">Data extraction</h3>
          <div className="text-[12px] text-muted-foreground">
            Capture structured data for every included study.
          </div>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() =>
            push.mutate(undefined, {
              onSuccess: () => {
                toast.success('Pushed to Results')
                navigate('/manuscript?section=Results')
              },
              onError: (e: Error) => toast.error(e.message),
            })
          }
          disabled={push.isPending || includedArticles.length === 0}
        >
          {push.isPending ? (
            <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />
          ) : (
            <Send className="h-3.5 w-3.5 mr-1.5" />
          )}
          Push to Results
        </Button>
      </header>

      {includedArticles.length === 0 ? (
        <div className="rounded-md border border-dashed border-border p-6 text-center text-[13px] text-muted-foreground">
          No included studies yet. Mark articles as <span className="font-medium">include</span> at the full-text stage.
        </div>
      ) : (
        <div className="space-y-4">
          {includedArticles.map((a) => (
            <StudyExtractionCard
              key={a.id}
              projectId={projectId}
              article={a}
              schema={schema}
              record={recordByArticle.get(a.id)}
            />
          ))}
        </div>
      )}
    </div>
  )
}

function StudyExtractionCard({
  projectId,
  article,
  schema,
  record,
}: {
  projectId: string
  article: Article
  schema: ExtractionFieldGroup[]
  record: ExtractionRecord | undefined
}) {
  const upsert = useUpsertExtraction(projectId)
  const update = useUpdateExtraction(projectId)

  const [fields, setFields] = useState<Record<string, Record<string, unknown>>>(
    () => deepCloneFields(record?.fields),
  )
  const [openGroups, setOpenGroups] = useState<Set<string>>(
    () => new Set(schema.map((g) => g.key)),
  )

  function setField(groupKey: string, fieldKey: string, value: unknown) {
    setFields((prev) => {
      const next = { ...prev }
      next[groupKey] = { ...(next[groupKey] ?? {}), [fieldKey]: value }
      return next
    })
  }

  function save() {
    const body = { fields }
    if (record) {
      update.mutate(
        { id: record.id, body },
        {
          onSuccess: () => toast.success('Extraction saved'),
          onError: (e: Error) => toast.error(e.message),
        },
      )
    } else {
      upsert.mutate(
        { article_id: article.id, ...body },
        {
          onSuccess: () => toast.success('Extraction saved'),
          onError: (e: Error) => toast.error(e.message),
        },
      )
    }
  }

  return (
    <div className="rounded-lg border border-border bg-white">
      <header className="px-4 py-3 border-b border-border">
        <div className="text-[13px] font-medium truncate">{article.title}</div>
        <div className="text-[11px] text-muted-foreground">
          {article.authors.slice(0, 3).join(', ')}
          {article.authors.length > 3 ? ' et al.' : ''}
          {article.year ? ` · ${article.year}` : ''}
        </div>
      </header>

      <div className="divide-y divide-border">
        {schema.map((group) => {
          const isOpen = openGroups.has(group.key)
          return (
            <div key={group.key}>
              <button
                type="button"
                onClick={() => {
                  setOpenGroups((s) => {
                    const next = new Set(s)
                    if (next.has(group.key)) next.delete(group.key)
                    else next.add(group.key)
                    return next
                  })
                }}
                className="w-full flex items-center justify-between px-4 py-2 bg-muted/20 hover:bg-muted/30 text-[12px] font-medium"
              >
                <span>{group.label}</span>
                <span className="text-muted-foreground text-[11px]">
                  {isOpen ? '−' : '+'}
                </span>
              </button>
              {isOpen && (
                <div className="px-4 py-3 grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {group.fields.map((f) => (
                    <FieldEditor
                      key={f.key}
                      field={f}
                      value={fields[group.key]?.[f.key]}
                      onChange={(v) => setField(group.key, f.key, v)}
                    />
                  ))}
                </div>
              )}
            </div>
          )
        })}
      </div>

      <footer className="px-4 py-3 flex justify-end border-t border-border">
        <Button
          size="sm"
          onClick={save}
          disabled={upsert.isPending || update.isPending}
          className="bg-accent hover:bg-accent-hover text-white"
        >
          {(upsert.isPending || update.isPending) && (
            <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />
          )}
          Save extraction
        </Button>
      </footer>
    </div>
  )
}

function deepCloneFields(
  src: Record<string, unknown> | undefined,
): Record<string, Record<string, unknown>> {
  const out: Record<string, Record<string, unknown>> = {}
  if (!src) return out
  for (const [k, v] of Object.entries(src)) {
    if (Array.isArray(v)) {
      // outcomes group stored as a bare list — wrap so the editor can find the
      // 'outcomes' field under the group object.
      out[k] = { outcomes: v }
    } else if (v && typeof v === 'object') {
      out[k] = { ...(v as Record<string, unknown>) }
    } else {
      out[k] = {}
    }
  }
  return out
}

function FieldEditor({
  field,
  value,
  onChange,
}: {
  field: ExtractionField
  value: unknown
  onChange: (v: unknown) => void
}) {
  const label = (
    <span className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
      {field.label}
      {field.required && <span className="text-rose-600 ml-1">*</span>}
    </span>
  )

  if (field.type === 'enum' && field.choices) {
    const cur = typeof value === 'string' ? value : ''
    return (
      <label className="block space-y-1">
        {label}
        <Select value={cur} onValueChange={(v) => onChange(v || null)}>
          <SelectTrigger className="h-8 text-[12px]">
            <SelectValue placeholder="—" />
          </SelectTrigger>
          <SelectContent>
            {field.choices.map((c) => (
              <SelectItem key={c} value={c}>
                {c}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </label>
    )
  }

  if (field.type === 'number') {
    const cur = typeof value === 'number' ? String(value) : (value as string) ?? ''
    return (
      <label className="block space-y-1">
        {label}
        <Input
          type="number"
          value={cur}
          onChange={(e) => {
            const v = e.target.value
            if (v === '') onChange(null)
            else {
              const n = Number(v)
              onChange(Number.isFinite(n) ? n : v)
            }
          }}
          className="h-8 text-[12px]"
        />
      </label>
    )
  }

  if (field.type === 'list') {
    // outcomes: one outcome per line, each is { name, ... } object
    const list = Array.isArray(value) ? (value as Array<{ name?: string }>) : []
    const text = list.map((o) => o.name ?? '').join('\n')
    return (
      <label className="block space-y-1 sm:col-span-2">
        {label}
        <Textarea
          value={text}
          onChange={(e) => {
            const lines = e.target.value
              .split('\n')
              .map((l) => l.trim())
              .filter(Boolean)
            onChange(lines.map((name) => ({ name })))
          }}
          placeholder="One outcome per line"
          rows={3}
          className="text-[12px]"
        />
      </label>
    )
  }

  const cur = typeof value === 'string' ? value : ''
  return (
    <label className="block space-y-1">
      {label}
      <Input
        value={cur}
        onChange={(e) => onChange(e.target.value)}
        className="h-8 text-[12px]"
      />
    </label>
  )
}
