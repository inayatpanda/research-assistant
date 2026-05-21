/**
 * Phase M0.5 — placeholder for the mobile Stats tab.
 *
 * M4 will replace this with a 5-page linear statistics wizard tuned
 * for touch input.
 */
import { BarChart3 } from 'lucide-react'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

export default function MobileStatsPlaceholder() {
  return (
    <div className="space-y-4 px-4 py-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-[15px]">
            <BarChart3 className="h-4 w-4" />
            Coming soon
          </CardTitle>
        </CardHeader>
        <CardContent className="text-[13px] text-muted-foreground">
          Phase M4 ships a touch-first statistics wizard — pick a dataset,
          choose a test, see the result + interpretation in five swipeable
          pages.
        </CardContent>
      </Card>
    </div>
  )
}
