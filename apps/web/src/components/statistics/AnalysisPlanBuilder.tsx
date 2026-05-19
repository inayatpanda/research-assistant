/**
 * Phase 13.5 (MP13.5) — Analysis plan builder.
 *
 * Lists existing plans for the project, lets the user create / rename /
 * delete one. Each plan is an ordered list of steps; the builder shows them
 * read-only here (steps are usually created via the "Save as plan" action on
 * an AnalysisResultCard). A free-text JSON editor is provided as an escape
 * hatch for power users.
 */
import { ListChecks, Loader2, Plus, Trash2 } from 'lucide-react'
import { useEffect, useState } from 'react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Skeleton } from '@/components/ui/skeleton'
import { Textarea } from '@/components/ui/textarea'
import type { AnalysisPlanRead, PlanStep } from '@/lib/api'
import {
  useAnalysisPlans,
  useCreateAnalysisPlan,
  useDeleteAnalysisPlan,
  useUpdateAnalysisPlan,
} from '@/hooks/useAnalysisPlans'

export function AnalysisPlanBuilder({ projectId }: { projectId: string }) {
  const { data: plans = [], isLoading } = useAnalysisPlans(projectId)
  const create = useCreateAnalysisPlan(projectId)
  const [newName, setNewName] = useState('')
  const [selectedId, setSelectedId] = useState<string | null>(null)

  useEffect(() => {
    if (!selectedId && plans.length > 0) {
      setSelectedId(plans[0].id)
    }
  }, [plans, selectedId])

  const selected = plans.find((p) => p.id === selectedId) ?? null

  function handleCreate() {
    if (!newName.trim()) {
      toast.error('Plan name is required.')
      return
    }
    create.mutate(
      { name: newName.trim(), steps: [] },
      {
        onSuccess: (p) => {
          toast.success('Plan created')
          setNewName('')
          setSelectedId(p.id)
        },
        onError: (e: Error) => toast.error(e.message),
      },
    )
  }

  return (
    <div className="space-y-4" data-testid="analysis-plan-builder">
      <div className="rounded-lg border border-border bg-white p-4 space-y-3">
        <div className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
          Analysis plans
        </div>
        <div className="flex items-end gap-2">
          <div className="flex-1">
            <Label htmlFor="plan-new-name">New plan name</Label>
            <Input
              id="plan-new-name"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder="e.g. Primary outcome workflow"
              data-testid="plan-new-name"
            />
          </div>
          <Button
            onClick={handleCreate}
            disabled={create.isPending}
            data-testid="plan-create"
          >
            {create.isPending ? (
              <Loader2 className="h-4 w-4 mr-1.5 animate-spin" />
            ) : (
              <Plus className="h-4 w-4 mr-1.5" />
            )}
            Create
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-[200px_1fr] gap-3">
        <aside className="space-y-2">
          {isLoading ? (
            <Skeleton className="h-[120px] rounded-md" />
          ) : plans.length === 0 ? (
            <div className="rounded-md border border-dashed border-border p-3 text-center text-[12px] text-muted-foreground">
              <ListChecks className="h-5 w-5 mx-auto mb-1" />
              No plans yet
            </div>
          ) : (
            <ul className="space-y-1.5">
              {plans.map((p) => (
                <li key={p.id}>
                  <button
                    type="button"
                    onClick={() => setSelectedId(p.id)}
                    className={`w-full text-left px-3 py-2 rounded-md border text-[13px] transition-colors ${
                      selectedId === p.id
                        ? 'border-accent bg-accent/5 text-foreground'
                        : 'border-border bg-white hover:border-accent/40'
                    }`}
                    data-testid={`plan-tab-${p.id}`}
                  >
                    <div className="font-medium truncate">{p.name}</div>
                    <div className="text-[11px] text-muted-foreground">
                      {p.steps.length} step{p.steps.length === 1 ? '' : 's'}
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </aside>

        <section>
          {selected ? (
            <PlanEditor
              key={selected.id}
              projectId={projectId}
              plan={selected}
              onDeleted={() => setSelectedId(null)}
            />
          ) : (
            <div className="rounded-lg border border-dashed border-border bg-white/40 p-6 text-center text-[13px] text-muted-foreground">
              Select or create a plan to edit its steps.
            </div>
          )}
        </section>
      </div>
    </div>
  )
}

function PlanEditor({
  projectId,
  plan,
  onDeleted,
}: {
  projectId: string
  plan: AnalysisPlanRead
  onDeleted: () => void
}) {
  const update = useUpdateAnalysisPlan(projectId)
  const del = useDeleteAnalysisPlan(projectId)
  const [name, setName] = useState(plan.name)
  const [description, setDescription] = useState(plan.description ?? '')
  const [stepsText, setStepsText] = useState(
    JSON.stringify(plan.steps ?? [], null, 2),
  )
  const [parseError, setParseError] = useState<string | null>(null)

  function save() {
    let parsed: PlanStep[] | null = null
    try {
      const out = JSON.parse(stepsText)
      if (!Array.isArray(out)) throw new Error('steps must be an array')
      parsed = out as PlanStep[]
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Invalid JSON'
      setParseError(msg)
      return
    }
    setParseError(null)
    update.mutate(
      {
        planId: plan.id,
        body: { name: name.trim() || plan.name, description, steps: parsed! },
      },
      {
        onSuccess: () => toast.success('Plan saved'),
        onError: (e: Error) => toast.error(e.message),
      },
    )
  }

  return (
    <div className="rounded-lg border border-border bg-white p-4 space-y-3">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <div>
          <Label htmlFor="plan-name">Name</Label>
          <Input
            id="plan-name"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </div>
        <div>
          <Label htmlFor="plan-desc">Description</Label>
          <Input
            id="plan-desc"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Optional"
          />
        </div>
      </div>
      <div>
        <Label htmlFor="plan-steps">Steps (JSON)</Label>
        <Textarea
          id="plan-steps"
          rows={10}
          value={stepsText}
          onChange={(e) => setStepsText(e.target.value)}
          className="font-mono text-[12px]"
          data-testid="plan-steps-json"
        />
        {parseError && (
          <p className="mt-1 text-[12px] text-rose-700">{parseError}</p>
        )}
        <p className="mt-1 text-[11px] text-muted-foreground">
          Each step is {`{ "type": "transform"|"test"|"plot", "args": {...} }`}.
          New steps are usually added via the "Save as plan" action on an
          analysis card or plot.
        </p>
      </div>
      <div className="flex items-center justify-end gap-2">
        <Button
          variant="outline"
          onClick={() => {
            if (
              confirm(`Delete plan "${plan.name}"? This cannot be undone.`)
            ) {
              del.mutate(plan.id, {
                onSuccess: () => {
                  toast.success('Plan deleted')
                  onDeleted()
                },
                onError: (e: Error) => toast.error(e.message),
              })
            }
          }}
          data-testid="plan-delete"
        >
          <Trash2 className="h-4 w-4 mr-1.5" />
          Delete
        </Button>
        <Button onClick={save} disabled={update.isPending} data-testid="plan-save">
          {update.isPending && (
            <Loader2 className="h-4 w-4 mr-1.5 animate-spin" />
          )}
          Save
        </Button>
      </div>
    </div>
  )
}
