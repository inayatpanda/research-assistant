/**
 * Phase M0.5 — placeholder for the mobile Learn tab.
 *
 * M1 will bring the full Learn hub (stat tests, reporting checklists,
 * economics, submission, walkthroughs) read-only to mobile.
 */
import { BookOpen } from 'lucide-react'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

export default function MobileLearnPlaceholder() {
  return (
    <div className="space-y-4 px-4 py-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-[15px]">
            <BookOpen className="h-4 w-4" />
            Coming soon
          </CardTitle>
        </CardHeader>
        <CardContent className="text-[13px] text-muted-foreground">
          Phase M1 brings the Learn hub to mobile — read every stat-test entry,
          reporting checklist and submission walkthrough in a touch-friendly
          layout.
        </CardContent>
      </Card>
    </div>
  )
}
