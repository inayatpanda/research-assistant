/**
 * Phase 5a — Card linking from Settings to the Learn hub.
 *
 * The Learn route is project-scoped (`/projects/:projectId/learn`) because
 * we expect future Phase 5c wiring (inline tooltips on the Statistics
 * page) to deep-link with project context. When no last-viewed project is
 * known yet, the link falls back to `/` so the user is sent to pick one.
 */
import { BookOpen, ChevronRight } from 'lucide-react'
import { Link } from 'react-router-dom'

import { Card, CardContent } from '@/components/ui/card'

interface Props {
  /** The current/last-viewed project id, if any. */
  projectId: string | null
}

export function LearnLink({ projectId }: Props) {
  const href = projectId ? `/projects/${projectId}/learn` : '/'
  return (
    <Card>
      <CardContent className="p-0">
        <Link
          to={href}
          data-testid="settings-learn-link"
          className="flex items-center gap-3 px-6 py-4 hover:bg-zinc-50 transition-colors"
        >
          <BookOpen className="h-4 w-4 text-muted-foreground shrink-0" />
          <div className="flex-1 min-w-0">
            <div className="text-[13px] font-medium">Learn · reference & how-to</div>
            <div className="text-[12px] text-muted-foreground">
              Curated reference cards for stat tests, with worked examples
              from orthopaedics, medicine and surgery.
            </div>
          </div>
          <ChevronRight className="h-4 w-4 text-muted-foreground" />
        </Link>
      </CardContent>
    </Card>
  )
}
