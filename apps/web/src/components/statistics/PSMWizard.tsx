import { ArrowRight, Loader2, Scale } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'

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
import type {
  Dataset,
  DatasetVariable,
  PSMResponse,
  VariableType,
} from '@/lib/api'
import { usePsm } from '@/hooks/usePsm'

function inferEffectiveType(v: DatasetVariable): VariableType {
  return v.user_type ?? v.inferred_type
}

function isBinaryNominal(v: DatasetVariable): boolean {
  const t = inferEffectiveType(v)
  if (t !== 'nominal' && t !== 'event_indicator') return false
  // Heuristic: sample shows at most 2 unique non-empty values.
  const uniq = new Set(
    v.sample_values
      .map((s) => s.trim())
      .filter((s) => s.length > 0),
  )
  return uniq.size <= 2
}

function isCovariate(v: DatasetVariable): boolean {
  const t = inferEffectiveType(v)
  return t === 'numeric' || t === 'ordinal' || t === 'nominal'
}

export function PSMWizard({
  open,
  onOpenChange,
  projectId,
  dataset,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  projectId: string
  dataset: Dataset | null
}) {
  const navigate = useNavigate()
  const psm = usePsm(projectId, dataset?.id ?? '')
  const [treatment, setTreatment] = useState<string>('')
  const [covariates, setCovariates] = useState<Set<string>>(new Set())
  const [caliper, setCaliper] = useState<string>('0.20')
  const [result, setResult] = useState<PSMResponse | null>(null)

  // Reset state every time the dialog opens with a (possibly new) dataset.
  useEffect(() => {
    if (open) {
      setTreatment('')
      setCovariates(new Set())
      setCaliper('0.20')
      setResult(null)
    }
  }, [open, dataset?.id])

  const treatmentOptions = useMemo(
    () => (dataset?.variables ?? []).filter(isBinaryNominal),
    [dataset],
  )
  const covariateOptions = useMemo(
    () =>
      (dataset?.variables ?? []).filter(
        (v) => isCovariate(v) && v.name !== treatment,
      ),
    [dataset, treatment],
  )

  function toggleCovariate(name: string) {
    setCovariates((prev) => {
      const next = new Set(prev)
      if (next.has(name)) next.delete(name)
      else next.add(name)
      return next
    })
  }

  function onRun() {
    if (!dataset) return
    if (!treatment) {
      toast.error('Pick a treatment column')
      return
    }
    if (covariates.size === 0) {
      toast.error('Pick at least one covariate')
      return
    }
    const cs = Number(caliper)
    if (!Number.isFinite(cs) || cs <= 0) {
      toast.error('Caliper must be a positive number')
      return
    }
    psm.mutate(
      {
        treatment_col: treatment,
        covariate_cols: Array.from(covariates),
        caliper_sd: cs,
      },
      {
        onSuccess: (r) => setResult(r),
        onError: (e) => toast.error(e.message),
      },
    )
  }

  function openMatched() {
    if (!result) return
    onOpenChange(false)
    navigate(
      `/projects/${projectId}/statistics?dataset=${result.matched_dataset_id}`,
    )
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl">
        <DialogHeader>
          <DialogTitle>Propensity score matching</DialogTitle>
          <DialogDescription>
            Match treated and control rows on a propensity score (logistic
            regression on covariates) using 1:1 nearest-neighbour with caliper.
          </DialogDescription>
        </DialogHeader>

        {result ? (
          <BalanceResult result={result} onOpenMatched={openMatched} />
        ) : (
          <div className="space-y-4" data-testid="psm-form">
            <div className="space-y-1.5">
              <Label htmlFor="psm-treatment">Treatment column (binary)</Label>
              <Select value={treatment} onValueChange={setTreatment}>
                <SelectTrigger
                  id="psm-treatment"
                  data-testid="psm-treatment"
                  disabled={treatmentOptions.length === 0}
                >
                  <SelectValue
                    placeholder={
                      treatmentOptions.length === 0
                        ? 'No binary nominal columns detected'
                        : 'Pick a treatment column'
                    }
                  />
                </SelectTrigger>
                <SelectContent>
                  {treatmentOptions.map((v) => (
                    <SelectItem key={v.id} value={v.name}>
                      {v.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1.5">
              <Label>Covariates</Label>
              <div className="rounded-md border border-border bg-white p-2 max-h-[200px] overflow-y-auto">
                {covariateOptions.length === 0 ? (
                  <div className="text-[12px] text-muted-foreground px-2 py-1">
                    {treatment
                      ? 'No eligible covariate columns'
                      : 'Pick a treatment column first'}
                  </div>
                ) : (
                  <ul className="space-y-0.5">
                    {covariateOptions.map((v) => {
                      const checked = covariates.has(v.name)
                      return (
                        <li key={v.id}>
                          <label className="flex items-center gap-2 px-2 py-1 rounded hover:bg-muted/50 cursor-pointer text-[13px]">
                            <input
                              type="checkbox"
                              checked={checked}
                              onChange={() => toggleCovariate(v.name)}
                              data-testid={`psm-cov-${v.name}`}
                            />
                            <span className="font-medium">{v.name}</span>
                            <span className="text-[11px] text-muted-foreground ml-auto capitalize">
                              {inferEffectiveType(v)}
                            </span>
                          </label>
                        </li>
                      )
                    })}
                  </ul>
                )}
              </div>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="psm-caliper">Caliper (SD multiplier)</Label>
              <Input
                id="psm-caliper"
                type="number"
                step="0.05"
                min="0.05"
                max="2"
                value={caliper}
                onChange={(e) => setCaliper(e.target.value)}
              />
              <div className="text-[11px] text-muted-foreground">
                Standard Rosenbaum-Rubin caliper is 0.2 × SD of the propensity
                score logit.
              </div>
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={() => onOpenChange(false)}>
                Cancel
              </Button>
              <Button
                onClick={onRun}
                disabled={psm.isPending || !dataset}
                className="bg-accent hover:bg-accent-hover text-white"
              >
                {psm.isPending ? (
                  <Loader2 className="h-4 w-4 mr-1.5 animate-spin" />
                ) : (
                  <Scale className="h-4 w-4 mr-1.5" />
                )}
                Run matching
              </Button>
            </DialogFooter>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}

function BalanceResult({
  result,
  onOpenMatched,
}: {
  result: PSMResponse
  onOpenMatched: () => void
}) {
  const beforeByCov = new Map(result.balance_before.map((r) => [r.covariate, r]))
  const afterByCov = new Map(result.balance_after.map((r) => [r.covariate, r]))
  const covariates = Array.from(
    new Set([
      ...result.balance_before.map((r) => r.covariate),
      ...result.balance_after.map((r) => r.covariate),
    ]),
  )

  return (
    <div className="space-y-4" data-testid="psm-result">
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        <Stat
          label="Treated matched"
          value={`${result.n_treated_matched}/${result.n_treated_total}`}
        />
        <Stat
          label="Control matched"
          value={`${result.n_control_matched}/${result.n_control_total}`}
        />
        <Stat
          label="Max SMD (pre)"
          value={result.max_smd_before.toFixed(3)}
        />
        <Stat
          label="Max SMD (post)"
          value={result.max_smd_after.toFixed(3)}
          highlight={result.max_smd_after < 0.1}
        />
      </div>
      <div className="rounded-lg border border-border bg-white overflow-hidden">
        <table className="w-full text-[12px]">
          <thead className="bg-muted/30 text-muted-foreground uppercase tracking-wider text-[10px]">
            <tr>
              <th className="text-left px-3 py-2 font-medium">Covariate</th>
              <th className="text-right px-3 py-2 font-medium">SMD before</th>
              <th className="text-right px-3 py-2 font-medium">SMD after</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border" data-testid="psm-balance-table">
            {covariates.map((cov) => {
              const b = beforeByCov.get(cov)
              const a = afterByCov.get(cov)
              return (
                <tr key={cov}>
                  <td className="px-3 py-2 font-medium">{cov}</td>
                  <td className="px-3 py-2 text-right tabular-nums">
                    {b ? b.smd.toFixed(3) : '—'}
                  </td>
                  <td
                    className={`px-3 py-2 text-right tabular-nums ${
                      a && Math.abs(a.smd) < 0.1
                        ? 'text-emerald-700 font-medium'
                        : ''
                    }`}
                  >
                    {a ? a.smd.toFixed(3) : '—'}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
      <DialogFooter>
        <Button
          onClick={onOpenMatched}
          className="bg-accent hover:bg-accent-hover text-white"
        >
          Open as dataset
          <ArrowRight className="h-4 w-4 ml-1.5" />
        </Button>
      </DialogFooter>
    </div>
  )
}

function Stat({
  label,
  value,
  highlight,
}: {
  label: string
  value: string
  highlight?: boolean
}) {
  return (
    <div className="rounded-md border border-border bg-muted/20 px-3 py-2">
      <div className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium">
        {label}
      </div>
      <div
        className={`mt-0.5 text-[13px] font-semibold tabular-nums ${
          highlight ? 'text-emerald-700' : ''
        }`}
      >
        {value}
      </div>
    </div>
  )
}
