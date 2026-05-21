/**
 * Phase M0.5 — placeholder for the mobile Manuscripts tab.
 *
 * M3 will replace this with a read-friendly manuscript view + an
 * edit sheet for per-paragraph rewrites.
 */
import { FileText } from 'lucide-react'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

export default function MobileManuscriptsPlaceholder() {
  return (
    <div className="space-y-4 px-4 py-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-[15px]">
            <FileText className="h-4 w-4" />
            Coming soon
          </CardTitle>
        </CardHeader>
        <CardContent className="text-[13px] text-muted-foreground">
          Phase M3 will let you read your manuscript, run AI rewrites
          paragraph-by-paragraph, and trigger a quick "polish prose" pass — all
          from your phone over the tailnet.
        </CardContent>
      </Card>
    </div>
  )
}
