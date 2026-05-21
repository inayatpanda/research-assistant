import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'

import { LearnTooltip } from '@/components/learn/LearnTooltip'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
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
import {
  articlesApi,
  screeningApi,
  type EffectMetric,
  type MetaAnalysisCreate,
  type PoolingModel,
} from '@/lib/api'
import { useCreateMeta } from '@/hooks/useMeta'

const METRICS: { value: EffectMetric; label: string }[] = [
  { value: 'md', label: 'Mean difference (MD)' },
  { value: 'smd', label: 'Standardised mean difference (SMD)' },
  { value: 'or', label: 'Odds ratio (OR)' },
  { value: 'rr', label: 'Risk ratio (RR)' },
  { value: 'hr', label: 'Hazard ratio (HR)' },
  { value: 'r', label: 'Correlation (r)' },
]

export function MetaAnalysisForm({
  projectId,
  onCreated,
}: {
  projectId: string
  onCreated?: (metaId: string) => void
}) {
  const [open, setOpen] = useState(false)
  const [title, setTitle] = useState('')
  const [metric, setMetric] = useState<EffectMetric>('smd')
  const [model, setModel] = useState<PoolingModel>('random')
  const [subgroupVar, setSubgroupVar] = useState<string>('')
  const [selectedArticleIds, setSelectedArticleIds] = useState<Set<string>>(new Set())

  const { mutateAsync: createMeta, isPending } = useCreateMeta(projectId)

  const { data: articles = [] } = useQuery({
    queryKey: ['articles', projectId, { sort: 'created_desc' }],
    queryFn: () => articlesApi.list(projectId, { sort: 'created_desc' }),
    enabled: open,
  })
  const { data: screening = [] } = useQuery({
    queryKey: ['screening', projectId, 'full_text'],
    queryFn: () => screeningApi.list(projectId, 'full_text'),
    enabled: open,
  })

  const includedArticles = useMemo(() => {
    const includedIds = new Set(
      screening.filter((s) => s.decision === 'include').map((s) => s.article_id),
    )
    return articles.filter((a) => includedIds.has(a.id))
  }, [articles, screening])

  const handleSubmit = async () => {
    if (selectedArticleIds.size < 2) return
    const body: MetaAnalysisCreate = {
      title: title || null,
      effect_metric: metric,
      model,
      subgroup_variable: subgroupVar || null,
      inputs: Array.from(selectedArticleIds).map((aid) => ({ article_id: aid })),
    }
    const created = await createMeta(body)
    setOpen(false)
    setTitle('')
    setSelectedArticleIds(new Set())
    onCreated?.(created.id)
  }

  const toggleArticle = (id: string) => {
    setSelectedArticleIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm">+ New meta-analysis</Button>
      </DialogTrigger>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>New meta-analysis</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="ma-title">Title</Label>
            <Input
              id="ma-title"
              placeholder="e.g. Pain at 6 weeks – SMD"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Effect metric</Label>
              <Select value={metric} onValueChange={(v) => setMetric(v as EffectMetric)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {METRICS.map((m) => (
                    <SelectItem key={m.value} value={m.value}>
                      {m.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>
                <LearnTooltip
                  concept="random-effects"
                  iconOnly
                  description="Random-effects models assume the true effect varies across studies; fixed-effect assumes one shared true effect."
                >
                  Pooling model
                </LearnTooltip>
              </Label>
              <Select value={model} onValueChange={(v) => setModel(v as PoolingModel)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="fixed">Fixed-effects (inverse-variance)</SelectItem>
                  <SelectItem value="random">Random-effects (DerSimonian-Laird)</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <div className="space-y-2">
            <Label htmlFor="ma-subgroup">Subgroup variable (optional)</Label>
            <Input
              id="ma-subgroup"
              placeholder="e.g. basic.design"
              value={subgroupVar}
              onChange={(e) => setSubgroupVar(e.target.value)}
            />
            <div className="text-[11px] text-muted-foreground">
              Dotted path into the extraction record (basic.design, intervention.name, …).
            </div>
          </div>
          <div className="space-y-2">
            <Label>Studies (full-text included)</Label>
            <div className="max-h-48 overflow-y-auto rounded-md border border-border bg-white">
              {includedArticles.length === 0 ? (
                <div className="px-3 py-4 text-[12px] text-muted-foreground">
                  No included studies yet. Mark articles as <em>include</em> at the full-text stage.
                </div>
              ) : (
                includedArticles.map((a) => (
                  <label
                    key={a.id}
                    className="flex items-start gap-2 px-3 py-2 border-b border-border last:border-b-0 cursor-pointer hover:bg-muted/30"
                  >
                    <input
                      type="checkbox"
                      checked={selectedArticleIds.has(a.id)}
                      onChange={() => toggleArticle(a.id)}
                      className="mt-1"
                    />
                    <div className="flex-1 min-w-0">
                      <div className="text-[13px] font-medium truncate">{a.title}</div>
                      <div className="text-[11px] text-muted-foreground">
                        {(a.authors || []).slice(0, 2).join(', ')}{a.year ? ` · ${a.year}` : ''}
                      </div>
                    </div>
                  </label>
                ))
              )}
            </div>
          </div>
        </div>
        <DialogFooter>
          <DialogClose asChild>
            <Button variant="outline">Cancel</Button>
          </DialogClose>
          <Button
            onClick={handleSubmit}
            disabled={isPending || selectedArticleIds.size < 2}
          >
            {isPending ? 'Creating…' : 'Create'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
