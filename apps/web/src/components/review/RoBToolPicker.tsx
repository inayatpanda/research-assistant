import { useEffect } from 'react'

import { LearnTooltip } from '@/components/learn/LearnTooltip'
import {
  ROB_TOOL_LABELS,
  RoBToolSchema,
  type RoBTool,
  type RoBToolDef,
} from '@/lib/api'
import { recommendToolForDesign } from '@/lib/rob'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

const ALL_TOOLS: RoBTool[] = RoBToolSchema.options

// Map each RoB tool to a Learn concept. AMSTAR-2 and the Newcastle-Ottawa
// fall back to robins-i in spirit because those Learn entries focus on
// the broader risk-of-bias domain.
const TOOL_LEARN_CONCEPT: Record<RoBTool, string> = {
  rob2: 'rob-2',
  robins_i: 'robins-i',
  nos: 'robins-i',
  amstar2: 'amstar-2',
}

export function RoBToolPicker({
  value,
  onChange,
  studyDesign,
  tools,
}: {
  value: RoBTool | null
  onChange: (t: RoBTool) => void
  studyDesign?: string | null
  tools?: RoBToolDef[]
}) {
  // Seed the recommended tool the first time we render, but never override
  // a user-picked value.
  useEffect(() => {
    if (value == null) {
      onChange(recommendToolForDesign(studyDesign))
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const available = tools?.map((t) => t.key as RoBTool) ?? ALL_TOOLS

  return (
    <div className="inline-flex items-center gap-1.5">
      <Select
        value={value ?? ''}
        onValueChange={(v) => onChange(v as RoBTool)}
      >
        <SelectTrigger className="w-[220px]">
          <SelectValue placeholder="Pick a tool" />
        </SelectTrigger>
        <SelectContent>
          {available.map((t) => (
            <SelectItem key={t} value={t}>
              {ROB_TOOL_LABELS[t]}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      {value && (
        <LearnTooltip
          concept={TOOL_LEARN_CONCEPT[value]}
          iconOnly
          description={`Open the Learn entry for ${ROB_TOOL_LABELS[value]}.`}
        >
          <span className="sr-only">{ROB_TOOL_LABELS[value]}</span>
        </LearnTooltip>
      )}
    </div>
  )
}
