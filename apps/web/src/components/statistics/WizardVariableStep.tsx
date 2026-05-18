import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  type Dataset,
  type DatasetVariable,
  type QuestionType,
  type VariableType,
} from '@/lib/api'

export type VariableSelection = {
  outcome?: string
  groups?: string
  x?: string
  y?: string
  covariates?: string[]
  time?: string
  event?: string
  rater_a?: string
  rater_b?: string
  paired?: boolean
}

export function VariablePickerStep({
  dataset,
  questionType,
  selection,
  onChange,
}: {
  dataset: Dataset
  questionType: QuestionType
  selection: VariableSelection
  onChange: (next: VariableSelection) => void
}) {
  const variables = dataset.variables
  const update = (patch: Partial<VariableSelection>) =>
    onChange({ ...selection, ...patch })

  if (questionType === 'group_comparison') {
    return (
      <div className="space-y-4">
        <VarField
          label="Outcome"
          help="The measurement you compare across groups"
          variables={filter(variables, ['numeric', 'ordinal', 'nominal'])}
          value={selection.outcome}
          onChange={(v) => update({ outcome: v })}
        />
        <VarField
          label="Group"
          help="The variable defining the groups"
          variables={filter(variables, ['nominal', 'ordinal'])}
          value={selection.groups}
          onChange={(v) => update({ groups: v })}
        />
        <label className="flex items-center gap-2 text-[13px]">
          <input
            type="checkbox"
            checked={!!selection.paired}
            onChange={(e) => update({ paired: e.target.checked })}
          />
          Paired or repeated measures
        </label>
      </div>
    )
  }

  if (questionType === 'association') {
    return (
      <div className="space-y-4">
        <VarField
          label="X (predictor)"
          variables={filter(variables, ['numeric', 'ordinal', 'nominal'])}
          value={selection.x}
          onChange={(v) => update({ x: v })}
        />
        <VarField
          label="Y (outcome)"
          variables={filter(variables, [
            'numeric',
            'ordinal',
            'nominal',
            'event_indicator',
          ])}
          value={selection.y}
          onChange={(v) => update({ y: v })}
        />
        <MultiVarField
          label="Additional covariates (optional)"
          variables={filter(variables, ['numeric', 'nominal', 'ordinal'])}
          value={selection.covariates ?? []}
          onChange={(arr) => update({ covariates: arr })}
        />
      </div>
    )
  }

  if (questionType === 'time_to_event') {
    return (
      <div className="space-y-4">
        <VarField
          label="Time"
          help="Follow-up duration"
          variables={filter(variables, ['numeric', 'time'])}
          value={selection.time}
          onChange={(v) => update({ time: v })}
        />
        <VarField
          label="Event indicator"
          help="1 = event, 0 = censored"
          variables={filter(variables, ['event_indicator', 'numeric', 'nominal'])}
          value={selection.event}
          onChange={(v) => update({ event: v })}
        />
        <VarField
          label="Group (optional)"
          variables={filter(variables, ['nominal', 'ordinal'])}
          value={selection.groups}
          onChange={(v) => update({ groups: v })}
          allowClear
        />
        <MultiVarField
          label="Covariates (optional)"
          variables={filter(variables, ['numeric', 'nominal', 'ordinal'])}
          value={selection.covariates ?? []}
          onChange={(arr) => update({ covariates: arr })}
        />
      </div>
    )
  }

  // agreement
  return (
    <div className="space-y-4">
      <VarField
        label="Rater A"
        variables={variables}
        value={selection.rater_a}
        onChange={(v) => update({ rater_a: v })}
      />
      <VarField
        label="Rater B"
        variables={variables}
        value={selection.rater_b}
        onChange={(v) => update({ rater_b: v })}
      />
    </div>
  )
}

function VarField({
  label,
  help,
  variables,
  value,
  onChange,
  allowClear = false,
}: {
  label: string
  help?: string
  variables: DatasetVariable[]
  value: string | undefined
  onChange: (v: string | undefined) => void
  allowClear?: boolean
}) {
  return (
    <div className="space-y-1">
      <div className="text-[12px] font-medium">{label}</div>
      {help && <div className="text-[11px] text-muted-foreground">{help}</div>}
      <Select
        value={value ?? ''}
        onValueChange={(v) => {
          if (allowClear && v === '__none__') {
            onChange(undefined)
          } else {
            onChange(v || undefined)
          }
        }}
      >
        <SelectTrigger className="h-9 text-[13px]">
          <SelectValue placeholder="Select a column…" />
        </SelectTrigger>
        <SelectContent>
          {allowClear && (
            <SelectItem value="__none__">
              <span className="text-muted-foreground">(none)</span>
            </SelectItem>
          )}
          {variables.map((v) => (
            <SelectItem key={v.id} value={v.name}>
              {v.name}
              <span className="ml-2 text-[11px] text-muted-foreground">
                {v.user_type ?? v.inferred_type}
              </span>
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  )
}

function MultiVarField({
  label,
  variables,
  value,
  onChange,
}: {
  label: string
  variables: DatasetVariable[]
  value: string[]
  onChange: (v: string[]) => void
}) {
  return (
    <div className="space-y-1">
      <div className="text-[12px] font-medium">{label}</div>
      <div className="rounded-md border border-border bg-white p-2 max-h-44 overflow-y-auto space-y-1">
        {variables.length === 0 && (
          <div className="text-[12px] text-muted-foreground px-1 py-1">
            No eligible columns
          </div>
        )}
        {variables.map((v) => {
          const checked = value.includes(v.name)
          return (
            <label
              key={v.id}
              className="flex items-center gap-2 text-[12px] hover:bg-muted/40 rounded px-1 py-0.5 cursor-pointer"
            >
              <input
                type="checkbox"
                checked={checked}
                onChange={(e) => {
                  if (e.target.checked) onChange([...value, v.name])
                  else onChange(value.filter((n) => n !== v.name))
                }}
              />
              <span className="font-medium">{v.name}</span>
              <span className="text-muted-foreground">
                {v.user_type ?? v.inferred_type}
              </span>
            </label>
          )
        })}
      </div>
    </div>
  )
}

function filter(
  variables: DatasetVariable[],
  allowed: VariableType[],
): DatasetVariable[] {
  const set = new Set(allowed)
  return variables.filter((v) => set.has(v.user_type ?? v.inferred_type))
}

export function isSelectionComplete(
  q: QuestionType,
  s: VariableSelection,
): boolean {
  if (q === 'group_comparison') return !!s.outcome && !!s.groups
  if (q === 'association') return !!s.x && !!s.y
  if (q === 'time_to_event') return !!s.time && !!s.event
  if (q === 'agreement') return !!s.rater_a && !!s.rater_b
  return false
}

export function buildVariablesPayload(
  q: QuestionType,
  s: VariableSelection,
): Record<string, string | string[]> {
  if (q === 'group_comparison') {
    const out: Record<string, string | string[]> = {
      outcome: s.outcome!,
      groups: s.groups!,
    }
    return out
  }
  if (q === 'association') {
    const out: Record<string, string | string[]> = { x: s.x!, y: s.y! }
    if (s.covariates && s.covariates.length > 0) out.covariates = s.covariates
    return out
  }
  if (q === 'time_to_event') {
    const out: Record<string, string | string[]> = {
      time: s.time!,
      event: s.event!,
    }
    if (s.groups) out.groups = s.groups
    if (s.covariates && s.covariates.length > 0) out.covariates = s.covariates
    return out
  }
  return { rater_a: s.rater_a!, rater_b: s.rater_b! }
}
