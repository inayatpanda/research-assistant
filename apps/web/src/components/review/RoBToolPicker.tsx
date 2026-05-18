import { useEffect } from 'react'

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
  )
}
