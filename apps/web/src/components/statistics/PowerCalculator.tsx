import { Calculator, Loader2 } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
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
import {
  POWER_FAMILY_LABELS,
  type PowerRequest,
  type PowerResponse,
  type PowerTestFamily,
} from '@/lib/api'
import { usePower } from '@/hooks/usePower'

const EFFECT_PRESETS: Record<
  PowerTestFamily,
  { small: number; medium: number; large: number; label: string }
> = {
  ttest_ind: { small: 0.2, medium: 0.5, large: 0.8, label: "Cohen's d" },
  ttest_paired: { small: 0.2, medium: 0.5, large: 0.8, label: "Cohen's dz" },
  anova: { small: 0.1, medium: 0.25, large: 0.4, label: "Cohen's f" },
  chi_square: { small: 0.1, medium: 0.3, large: 0.5, label: "Cohen's w" },
  correlation: { small: 0.1, medium: 0.3, large: 0.5, label: '|r|' },
}

export function PowerCalculatorDialog({
  open,
  onOpenChange,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl">
        <DialogHeader>
          <DialogTitle>Power calculator</DialogTitle>
          <DialogDescription>
            Compute the sample size required to detect an effect at a given
            significance and power.
          </DialogDescription>
        </DialogHeader>
        <PowerCalculator />
      </DialogContent>
    </Dialog>
  )
}

export function PowerCalculator() {
  const [family, setFamily] = useState<PowerTestFamily>('ttest_ind')
  const [effectSize, setEffectSize] = useState<string>('0.5')
  const [alpha, setAlpha] = useState<string>('0.05')
  const [power, setPower] = useState<string>('0.80')
  const [kGroups, setKGroups] = useState<string>('3')
  const [df, setDf] = useState<string>('1')
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<PowerResponse | null>(null)
  const mutation = usePower()

  function presets() {
    return EFFECT_PRESETS[family]
  }

  function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    const es = Number(effectSize)
    const a = Number(alpha)
    const p = Number(power)
    if (!Number.isFinite(es) || es <= 0) {
      setError('Effect size must be a positive number')
      return
    }
    if (!(a > 0 && a < 1)) {
      setError('α must be between 0 and 1 (exclusive)')
      return
    }
    if (!(p > 0 && p < 1)) {
      setError('Power must be between 0 and 1 (exclusive)')
      return
    }
    const body: PowerRequest = {
      test_family: family,
      effect_size: es,
      alpha: a,
      power: p,
    }
    if (family === 'anova') {
      const k = Number(kGroups)
      if (!Number.isFinite(k) || k < 2) {
        setError('k_groups must be ≥ 2 for ANOVA')
        return
      }
      body.k_groups = k
    }
    if (family === 'chi_square') {
      const d = Number(df)
      if (!Number.isFinite(d) || d < 1) {
        setError('df must be ≥ 1 for chi-square')
        return
      }
      body.df = d
    }
    mutation.mutate(body, {
      onSuccess: (r) => setResult(r),
      onError: (e) => {
        setError(e.message)
        toast.error(e.message)
      },
    })
  }

  const cur = presets()

  return (
    <form
      onSubmit={onSubmit}
      className="grid grid-cols-1 md:grid-cols-2 gap-6"
      data-testid="power-calculator"
    >
      <div className="space-y-4">
        <div className="space-y-1.5">
          <Label htmlFor="power-family">Test family</Label>
          <Select
            value={family}
            onValueChange={(v) => {
              const next = v as PowerTestFamily
              setFamily(next)
              setEffectSize(String(EFFECT_PRESETS[next].medium))
            }}
          >
            <SelectTrigger id="power-family" data-testid="power-family">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {Object.entries(POWER_FAMILY_LABELS).map(([key, label]) => (
                <SelectItem key={key} value={key}>
                  {label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="power-effect">Effect size ({cur.label})</Label>
          <Input
            id="power-effect"
            type="number"
            step="0.01"
            value={effectSize}
            onChange={(e) => setEffectSize(e.target.value)}
            data-testid="power-effect-size"
          />
          <div className="flex gap-1.5 pt-1">
            <Button
              type="button"
              size="sm"
              variant="outline"
              className="h-7 text-[11px]"
              onClick={() => setEffectSize(String(cur.small))}
            >
              Small ({cur.small})
            </Button>
            <Button
              type="button"
              size="sm"
              variant="outline"
              className="h-7 text-[11px]"
              onClick={() => setEffectSize(String(cur.medium))}
            >
              Medium ({cur.medium})
            </Button>
            <Button
              type="button"
              size="sm"
              variant="outline"
              className="h-7 text-[11px]"
              onClick={() => setEffectSize(String(cur.large))}
            >
              Large ({cur.large})
            </Button>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1.5">
            <Label htmlFor="power-alpha">α</Label>
            <Input
              id="power-alpha"
              type="number"
              step="0.01"
              value={alpha}
              onChange={(e) => setAlpha(e.target.value)}
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="power-power">Power</Label>
            <Input
              id="power-power"
              type="number"
              step="0.01"
              value={power}
              onChange={(e) => setPower(e.target.value)}
            />
          </div>
        </div>

        {family === 'anova' && (
          <div className="space-y-1.5">
            <Label htmlFor="power-k">k (groups)</Label>
            <Input
              id="power-k"
              type="number"
              min="2"
              step="1"
              value={kGroups}
              onChange={(e) => setKGroups(e.target.value)}
            />
          </div>
        )}

        {family === 'chi_square' && (
          <div className="space-y-1.5">
            <Label htmlFor="power-df">df</Label>
            <Input
              id="power-df"
              type="number"
              min="1"
              step="1"
              value={df}
              onChange={(e) => setDf(e.target.value)}
            />
          </div>
        )}

        {error && (
          <div
            className="rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-[12px] text-rose-800"
            role="alert"
          >
            {error}
          </div>
        )}

        <Button
          type="submit"
          disabled={mutation.isPending}
          className="bg-accent hover:bg-accent-hover text-white"
        >
          {mutation.isPending ? (
            <Loader2 className="h-4 w-4 mr-1.5 animate-spin" />
          ) : (
            <Calculator className="h-4 w-4 mr-1.5" />
          )}
          Calculate
        </Button>
      </div>

      <div className="space-y-3">
        {result ? (
          <>
            <div className="rounded-md border border-border bg-muted/20 p-4 space-y-2">
              <div className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
                Required sample size
              </div>
              <div
                className="text-3xl font-semibold tabular-nums"
                data-testid="power-required-n"
              >
                n = {result.required_n}
              </div>
              {result.required_n_per_group !== null && (
                <div className="text-[12px] text-muted-foreground">
                  {result.required_n_per_group} per group
                </div>
              )}
              <div className="text-[12px] text-muted-foreground">
                α = {result.alpha} · power = {result.power} · effect ={' '}
                {result.effect_size}
              </div>
              {result.notes && (
                <div className="text-[11px] text-muted-foreground italic">
                  {result.notes}
                </div>
              )}
            </div>
            {result.sensitivity_curve_png && (
              <div className="rounded-md border border-border bg-white overflow-hidden">
                <img
                  src={result.sensitivity_curve_png}
                  alt="Sensitivity curve"
                  className="w-full h-auto"
                  data-testid="power-sensitivity-curve"
                />
              </div>
            )}
          </>
        ) : (
          <div className="rounded-md border border-dashed border-border bg-muted/20 p-8 text-center text-[13px] text-muted-foreground">
            Enter parameters and click <span className="font-medium">Calculate</span>{' '}
            to see required sample size and a sensitivity curve.
          </div>
        )}
      </div>
    </form>
  )
}
