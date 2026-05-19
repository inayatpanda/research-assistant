import { Loader2 } from 'lucide-react'
import { useMemo, useState } from 'react'
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
import { Textarea } from '@/components/ui/textarea'
import type {
  GradeAssessmentCreate,
  GradeAssessmentRead,
  GradeDowngradeLevel,
  GradeSmallUpgrade,
  GradeStartingCertainty,
  GradeUpgradeLevel,
} from '@/lib/api'
import {
  CERTAINTY_LABEL,
  CERTAINTY_SYMBOL,
  deriveCertainty,
} from '@/lib/grade'
import { useUpsertGrade } from '@/hooks/useGrade'

const DOWNGRADE_OPTIONS: { value: GradeDowngradeLevel; label: string }[] = [
  { value: 'not_serious', label: 'Not serious' },
  { value: 'serious', label: 'Serious (-1)' },
  { value: 'very_serious', label: 'Very serious (-2)' },
]

const SMALL_UPGRADE_OPTIONS: { value: GradeSmallUpgrade; label: string }[] = [
  { value: 'none', label: 'None' },
  { value: 'present', label: 'Present (+1)' },
]

const LARGE_EFFECT_OPTIONS: { value: GradeUpgradeLevel; label: string }[] = [
  { value: 'none', label: 'None' },
  { value: 'present', label: 'Large (+1)' },
  { value: 'large', label: 'Very large (+2)' },
]

export function GRADEAssessmentForm({
  projectId,
  existing,
  onSaved,
}: {
  projectId: string
  existing?: GradeAssessmentRead
  onSaved?: () => void
}) {
  const upsert = useUpsertGrade(projectId)

  const [outcomeLabel, setOutcomeLabel] = useState(
    existing?.outcome_label ?? '',
  )
  const [starting, setStarting] = useState<GradeStartingCertainty>(
    existing?.starting_certainty ?? 'high',
  )
  const [riskOfBias, setRiskOfBias] = useState<GradeDowngradeLevel>(
    existing?.domain_risk_of_bias ?? 'not_serious',
  )
  const [inconsistency, setInconsistency] = useState<GradeDowngradeLevel>(
    existing?.domain_inconsistency ?? 'not_serious',
  )
  const [indirectness, setIndirectness] = useState<GradeDowngradeLevel>(
    existing?.domain_indirectness ?? 'not_serious',
  )
  const [imprecision, setImprecision] = useState<GradeDowngradeLevel>(
    existing?.domain_imprecision ?? 'not_serious',
  )
  const [publicationBias, setPublicationBias] = useState<GradeDowngradeLevel>(
    existing?.domain_publication_bias ?? 'not_serious',
  )
  const [largeEffect, setLargeEffect] = useState<GradeUpgradeLevel>(
    existing?.upgrade_large_effect ?? 'none',
  )
  const [doseResponse, setDoseResponse] = useState<GradeSmallUpgrade>(
    existing?.upgrade_dose_response ?? 'none',
  )
  const [confoundersAgainst, setConfoundersAgainst] =
    useState<GradeSmallUpgrade>(
      existing?.upgrade_confounders_against ?? 'none',
    )
  const [notes, setNotes] = useState(existing?.notes ?? '')

  const derivedCertainty = useMemo(
    () =>
      deriveCertainty(
        starting,
        {
          risk_of_bias: riskOfBias,
          inconsistency,
          indirectness,
          imprecision,
          publication_bias: publicationBias,
        },
        {
          large_effect: largeEffect,
          dose_response: doseResponse,
          confounders_against: confoundersAgainst,
        },
      ),
    [
      starting,
      riskOfBias,
      inconsistency,
      indirectness,
      imprecision,
      publicationBias,
      largeEffect,
      doseResponse,
      confoundersAgainst,
    ],
  )

  function save() {
    if (!outcomeLabel.trim()) {
      toast.error('Outcome label is required')
      return
    }
    const body: GradeAssessmentCreate = {
      outcome_label: outcomeLabel.trim(),
      starting_certainty: starting,
      domain_risk_of_bias: riskOfBias,
      domain_inconsistency: inconsistency,
      domain_indirectness: indirectness,
      domain_imprecision: imprecision,
      domain_publication_bias: publicationBias,
      upgrade_large_effect: largeEffect,
      upgrade_dose_response: doseResponse,
      upgrade_confounders_against: confoundersAgainst,
      notes: notes.trim() || null,
      meta_id: existing?.meta_id ?? null,
    }
    upsert.mutate(body, {
      onSuccess: () => {
        toast.success('GRADE assessment saved')
        onSaved?.()
      },
      onError: () => toast.error('Failed to save GRADE assessment'),
    })
  }

  return (
    <div className="space-y-5 rounded border p-4">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <div>
          <Label htmlFor="grade-outcome">Outcome label</Label>
          <Input
            id="grade-outcome"
            data-testid="grade-outcome"
            value={outcomeLabel}
            onChange={(e) => setOutcomeLabel(e.target.value)}
            placeholder="e.g. All-cause mortality at 12 months"
          />
        </div>
        <div>
          <Label>Starting certainty</Label>
          <div className="mt-2 flex gap-3">
            <label className="flex items-center gap-2 text-sm">
              <input
                type="radio"
                name="starting"
                value="high"
                checked={starting === 'high'}
                onChange={() => setStarting('high')}
              />
              High (RCTs)
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="radio"
                name="starting"
                value="low"
                checked={starting === 'low'}
                onChange={() => setStarting('low')}
              />
              Low (observational)
            </label>
          </div>
        </div>
      </div>

      <fieldset className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <legend className="text-sm font-medium">Downgrade domains</legend>
        <DomainSelect
          label="Risk of bias"
          value={riskOfBias}
          onChange={setRiskOfBias}
          options={DOWNGRADE_OPTIONS}
        />
        <DomainSelect
          label="Inconsistency"
          value={inconsistency}
          onChange={setInconsistency}
          options={DOWNGRADE_OPTIONS}
        />
        <DomainSelect
          label="Indirectness"
          value={indirectness}
          onChange={setIndirectness}
          options={DOWNGRADE_OPTIONS}
        />
        <DomainSelect
          label="Imprecision"
          value={imprecision}
          onChange={setImprecision}
          options={DOWNGRADE_OPTIONS}
        />
        <DomainSelect
          label="Publication bias"
          value={publicationBias}
          onChange={setPublicationBias}
          options={DOWNGRADE_OPTIONS}
        />
      </fieldset>

      <fieldset className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <legend className="text-sm font-medium">Upgrade domains</legend>
        <DomainSelect
          label="Large effect"
          value={largeEffect}
          onChange={setLargeEffect}
          options={LARGE_EFFECT_OPTIONS}
        />
        <DomainSelect
          label="Dose-response gradient"
          value={doseResponse}
          onChange={setDoseResponse}
          options={SMALL_UPGRADE_OPTIONS}
        />
        <DomainSelect
          label="Confounders bias against effect"
          value={confoundersAgainst}
          onChange={setConfoundersAgainst}
          options={SMALL_UPGRADE_OPTIONS}
        />
      </fieldset>

      <div>
        <Label htmlFor="grade-notes">Notes (optional)</Label>
        <Textarea
          id="grade-notes"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          rows={3}
        />
      </div>

      <div className="flex items-center justify-between">
        <div
          className={`cert cert-${derivedCertainty} rounded px-3 py-1 text-sm font-medium`}
          data-testid="grade-certainty-badge"
          data-certainty={derivedCertainty}
        >
          Certainty: {CERTAINTY_LABEL[derivedCertainty]}{' '}
          {CERTAINTY_SYMBOL[derivedCertainty]}
        </div>
        <Button onClick={save} disabled={upsert.isPending}>
          {upsert.isPending ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Saving…
            </>
          ) : (
            'Save'
          )}
        </Button>
      </div>
    </div>
  )
}

function DomainSelect<T extends string>({
  label,
  value,
  onChange,
  options,
}: {
  label: string
  value: T
  onChange: (v: T) => void
  options: { value: T; label: string }[]
}) {
  return (
    <div>
      <Label>{label}</Label>
      <Select value={value} onValueChange={(v) => onChange(v as T)}>
        <SelectTrigger className="mt-1" aria-label={label}>
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {options.map((o) => (
            <SelectItem key={o.value} value={o.value}>
              {o.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  )
}
