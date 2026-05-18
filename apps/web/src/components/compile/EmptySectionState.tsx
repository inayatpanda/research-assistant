import { ArrowRight } from 'lucide-react'
import { Link } from 'react-router-dom'

import type { HighlightColour } from '@/lib/api'
import { useProjectId } from '@/lib/projectContext'
import { highlightColors, sectionLabels } from '@/lib/tokens'

export function EmptySectionState({ colour }: { colour: HighlightColour }) {
  const projectId = useProjectId()
  const palette = highlightColors[colour]
  return (
    <div className="rounded-lg border border-dashed border-border bg-white/40 p-10 text-center">
      <div
        className="mx-auto h-8 w-8 rounded-full"
        style={{ background: palette.fill, border: `2px solid ${palette.solid}` }}
      />
      <div className="mt-3 text-[14px] font-medium">
        No {sectionLabels[colour]} highlights yet
      </div>
      <div className="mt-1 text-[13px] text-muted-foreground max-w-md mx-auto">
        Open an article in the Reader, select a passage, and pick the{' '}
        <span className="font-medium" style={{ color: palette.solid }}>
          {sectionLabels[colour]}
        </span>{' '}
        colour to add it here.
      </div>
      <Link
        to={`/projects/${projectId}/library`}
        className="mt-4 inline-flex items-center gap-1 text-[13px] text-accent hover:underline"
      >
        Go to Library
        <ArrowRight className="h-3 w-3" />
      </Link>
    </div>
  )
}
