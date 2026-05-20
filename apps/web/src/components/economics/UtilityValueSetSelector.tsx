import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useUtilityValueSets } from '@/hooks/useEconomicAnalyses'

export interface UtilityValueSetSelectorProps {
  value: string
  onChange: (next: string) => void
  disabled?: boolean
}

/**
 * MP18 — Drop-down for picking which utility value set the analysis uses.
 *
 * Reads from /api/utility-value-sets which is a static server-side
 * catalogue (no licence fee — all four tariffs are publicly published).
 */
export function UtilityValueSetSelector({
  value,
  onChange,
  disabled = false,
}: UtilityValueSetSelectorProps) {
  const { data, isLoading } = useUtilityValueSets()
  return (
    <Select value={value} onValueChange={onChange} disabled={disabled || isLoading}>
      <SelectTrigger aria-label="Utility value set">
        <SelectValue placeholder={isLoading ? 'Loading…' : 'Pick a value set'} />
      </SelectTrigger>
      <SelectContent>
        {(data ?? []).map((vs) => (
          <SelectItem key={vs.key} value={vs.key}>
            {vs.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}
