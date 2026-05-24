import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Label } from '@/components/ui/label'
import type { DatasetVariable, VariableType } from '@/lib/api'

export type ColumnPickerProps = {
  label: string
  variables: DatasetVariable[]
  value: string | null
  onChange: (v: string | null) => void
  /** Only show columns whose effective type matches one of these.
   * "any" lets every column through. */
  acceptedTypes?: VariableType[] | 'any'
  placeholder?: string
  helpText?: string
  disabled?: boolean
  /** Pass an `id` so we can match the `Label htmlFor`. */
  id?: string
}

export function effectiveType(v: DatasetVariable): VariableType {
  return v.user_type ?? v.inferred_type
}

export function displayName(v: DatasetVariable): string {
  return (v.display_label && v.display_label.trim()) || v.name
}

export function ColumnPicker({
  label,
  variables,
  value,
  onChange,
  acceptedTypes = 'any',
  placeholder = 'Select a column',
  helpText,
  disabled,
  id,
}: ColumnPickerProps) {
  const filtered =
    acceptedTypes === 'any'
      ? variables
      : variables.filter((v) => acceptedTypes.includes(effectiveType(v)))
  const empty = filtered.length === 0
  const pickerId = id ?? `column-picker-${label.replace(/\s+/g, '-').toLowerCase()}`
  return (
    <div className="space-y-1.5">
      <Label htmlFor={pickerId} className="text-xs font-medium text-muted-foreground">
        {label}
      </Label>
      <Select
        value={value ?? ''}
        onValueChange={(v) => onChange(v || null)}
        disabled={disabled || empty}
      >
        <SelectTrigger id={pickerId} aria-label={label}>
          <SelectValue placeholder={empty ? 'No matching columns' : placeholder} />
        </SelectTrigger>
        <SelectContent>
          {filtered.map((v) => (
            <SelectItem key={v.id} value={v.name}>
              <span className="font-medium">{displayName(v)}</span>
              <span className="ml-2 text-[11px] text-muted-foreground">
                {effectiveType(v)}
              </span>
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      {helpText ? (
        <p className="text-[11px] text-muted-foreground">{helpText}</p>
      ) : null}
    </div>
  )
}

/** Multi-select column picker rendered as a checkbox list. */
export function MultiColumnPicker({
  label,
  variables,
  value,
  onChange,
  acceptedTypes = 'any',
  helpText,
  disabled,
}: Omit<ColumnPickerProps, 'value' | 'onChange'> & {
  value: string[]
  onChange: (v: string[]) => void
}) {
  const filtered =
    acceptedTypes === 'any'
      ? variables
      : variables.filter((v) => acceptedTypes.includes(effectiveType(v)))
  const toggle = (name: string) => {
    if (value.includes(name)) onChange(value.filter((v) => v !== name))
    else onChange([...value, name])
  }
  return (
    <div className="space-y-1.5">
      <Label className="text-xs font-medium text-muted-foreground">{label}</Label>
      {filtered.length === 0 ? (
        <p className="text-xs text-muted-foreground italic">No matching columns</p>
      ) : (
        <ul className="rounded border border-border divide-y max-h-48 overflow-auto">
          {filtered.map((v) => (
            <li key={v.id}>
              <label
                className={
                  'flex items-center gap-2 px-2 py-1.5 text-sm cursor-pointer hover:bg-muted ' +
                  (disabled ? 'pointer-events-none opacity-50' : '')
                }
              >
                <input
                  type="checkbox"
                  checked={value.includes(v.name)}
                  onChange={() => toggle(v.name)}
                  className="h-4 w-4"
                  disabled={disabled}
                  aria-label={`Select ${displayName(v)}`}
                />
                <span className="flex-1 truncate font-medium">{displayName(v)}</span>
                <span className="text-[11px] text-muted-foreground">
                  {effectiveType(v)}
                </span>
              </label>
            </li>
          ))}
        </ul>
      )}
      {helpText ? (
        <p className="text-[11px] text-muted-foreground">{helpText}</p>
      ) : null}
    </div>
  )
}
