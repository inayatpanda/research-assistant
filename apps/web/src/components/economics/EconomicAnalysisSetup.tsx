import { useState } from 'react'

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
import type {
  EconomicAnalysisCreateBody,
  EconomicCurrency,
  EconomicPerspective,
  UtilityValueSetKey,
} from '@/lib/api'

import { UtilityValueSetSelector } from './UtilityValueSetSelector'

export interface EconomicAnalysisSetupProps {
  /** Optional initial values when editing an existing analysis. */
  initial?: Partial<EconomicAnalysisCreateBody>
  onSubmit: (body: EconomicAnalysisCreateBody) => void
  submitting?: boolean
  submitLabel?: string
}

const CURRENCIES: EconomicCurrency[] = ['GBP', 'USD', 'EUR', 'AUD', 'CAD', 'Other']
const PERSPECTIVES: EconomicPerspective[] = [
  'patient',
  'healthcare_system',
  'societal',
]

/**
 * MP18 — Multi-field setup form for an EconomicAnalysis.
 *
 * Collects: name, currency, time horizon, perspective, discount rates,
 * WTP thresholds, utility value set, bootstrap n + seed, treatment column,
 * intervention/comparator labels. Cost-column bindings are gathered by
 * the sibling CostColumnBinder component once the analysis exists.
 */
export function EconomicAnalysisSetup({
  initial,
  onSubmit,
  submitting = false,
  submitLabel = 'Create analysis',
}: EconomicAnalysisSetupProps) {
  const [name, setName] = useState(initial?.name ?? '')
  const [currency, setCurrency] = useState<EconomicCurrency>(
    (initial?.currency as EconomicCurrency) ?? 'GBP',
  )
  const [timeHorizon, setTimeHorizon] = useState(
    initial?.time_horizon_months ?? 12,
  )
  const [perspective, setPerspective] = useState<EconomicPerspective>(
    (initial?.perspective as EconomicPerspective) ?? 'healthcare_system',
  )
  const [discCosts, setDiscCosts] = useState(initial?.discount_rate_costs ?? 0.035)
  const [discQalys, setDiscQalys] = useState(initial?.discount_rate_qalys ?? 0.035)
  const [wtpRaw, setWtpRaw] = useState(
    (initial?.wtp_thresholds ?? [20000, 30000]).join(','),
  )
  const [valueSet, setValueSet] = useState<UtilityValueSetKey>(
    (initial?.utility_value_set as UtilityValueSetKey) ?? 'EQ5D_5L_UK',
  )
  const [bootstrapN, setBootstrapN] = useState(initial?.bootstrap_n ?? 1000)
  const [seed, setSeed] = useState(initial?.seed ?? 42)
  const [treatmentCol, setTreatmentCol] = useState(initial?.treatment_col ?? '')
  const [comparatorLabel, setComparatorLabel] = useState(
    initial?.comparator_label ?? '',
  )
  const [interventionLabel, setInterventionLabel] = useState(
    initial?.intervention_label ?? '',
  )

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const wtp = wtpRaw
      .split(',')
      .map((s) => Number(s.trim()))
      .filter((n) => !Number.isNaN(n) && n >= 0)
    onSubmit({
      name,
      currency,
      time_horizon_months: timeHorizon,
      perspective,
      discount_rate_costs: discCosts,
      discount_rate_qalys: discQalys,
      wtp_thresholds: wtp.length ? wtp : [20000, 30000],
      utility_value_set: valueSet,
      bootstrap_n: bootstrapN,
      seed,
      treatment_col: treatmentCol,
      comparator_label: comparatorLabel,
      intervention_label: interventionLabel,
      cost_columns: initial?.cost_columns ?? [],
    })
  }

  return (
    <form
      data-testid="economic-analysis-setup"
      onSubmit={handleSubmit}
      className="space-y-4"
    >
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <Label htmlFor="econ-name">Analysis name</Label>
          <Input
            id="econ-name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Anterior vs control CEA"
            required
          />
        </div>
        <div>
          <Label htmlFor="econ-currency">Currency</Label>
          <Select
            value={currency}
            onValueChange={(v) => setCurrency(v as EconomicCurrency)}
          >
            <SelectTrigger id="econ-currency"><SelectValue /></SelectTrigger>
            <SelectContent>
              {CURRENCIES.map((c) => (
                <SelectItem key={c} value={c}>{c}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div>
          <Label htmlFor="econ-horizon">Time horizon (months)</Label>
          <Input
            id="econ-horizon"
            type="number"
            min={1}
            max={600}
            value={timeHorizon}
            onChange={(e) => setTimeHorizon(Number(e.target.value) || 12)}
          />
        </div>
        <div>
          <Label htmlFor="econ-perspective">Perspective</Label>
          <Select
            value={perspective}
            onValueChange={(v) => setPerspective(v as EconomicPerspective)}
          >
            <SelectTrigger id="econ-perspective"><SelectValue /></SelectTrigger>
            <SelectContent>
              {PERSPECTIVES.map((p) => (
                <SelectItem key={p} value={p}>{p.replace('_', ' ')}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div>
          <Label htmlFor="econ-disc-costs">Discount rate (costs)</Label>
          <Input
            id="econ-disc-costs"
            type="number"
            step={0.005}
            min={0}
            max={0.5}
            value={discCosts}
            onChange={(e) => setDiscCosts(Number(e.target.value) || 0)}
          />
        </div>
        <div>
          <Label htmlFor="econ-disc-qalys">Discount rate (QALYs)</Label>
          <Input
            id="econ-disc-qalys"
            type="number"
            step={0.005}
            min={0}
            max={0.5}
            value={discQalys}
            onChange={(e) => setDiscQalys(Number(e.target.value) || 0)}
          />
        </div>
        <div className="md:col-span-2">
          <Label htmlFor="econ-wtp">WTP thresholds (comma-separated)</Label>
          <Input
            id="econ-wtp"
            value={wtpRaw}
            onChange={(e) => setWtpRaw(e.target.value)}
            placeholder="20000,30000"
          />
        </div>
        <div>
          <Label>Utility value set</Label>
          <UtilityValueSetSelector
            value={valueSet}
            onChange={(v) => setValueSet(v as UtilityValueSetKey)}
          />
        </div>
        <div className="grid grid-cols-2 gap-2">
          <div>
            <Label htmlFor="econ-bootstrap">Bootstrap n</Label>
            <Input
              id="econ-bootstrap"
              type="number"
              min={100}
              max={10000}
              value={bootstrapN}
              onChange={(e) => setBootstrapN(Number(e.target.value) || 1000)}
            />
          </div>
          <div>
            <Label htmlFor="econ-seed">Seed</Label>
            <Input
              id="econ-seed"
              type="number"
              min={0}
              value={seed}
              onChange={(e) => setSeed(Number(e.target.value) || 0)}
            />
          </div>
        </div>
        <div>
          <Label htmlFor="econ-treatment-col">Treatment column</Label>
          <Input
            id="econ-treatment-col"
            value={treatmentCol}
            onChange={(e) => setTreatmentCol(e.target.value)}
            placeholder="treatment"
            required
          />
        </div>
        <div className="grid grid-cols-2 gap-2">
          <div>
            <Label htmlFor="econ-intervention">Intervention label</Label>
            <Input
              id="econ-intervention"
              value={interventionLabel}
              onChange={(e) => setInterventionLabel(e.target.value)}
              placeholder="anterior"
              required
            />
          </div>
          <div>
            <Label htmlFor="econ-comparator">Comparator label</Label>
            <Input
              id="econ-comparator"
              value={comparatorLabel}
              onChange={(e) => setComparatorLabel(e.target.value)}
              placeholder="control"
              required
            />
          </div>
        </div>
      </div>
      <div className="flex justify-end">
        <Button type="submit" disabled={submitting}>
          {submitLabel}
        </Button>
      </div>
    </form>
  )
}
