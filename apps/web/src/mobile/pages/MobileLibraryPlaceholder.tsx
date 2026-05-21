/**
 * Phase M0.5 — placeholder for the mobile Library tab.
 *
 * M2 will replace this with the real read-only library + reader UI.
 */
import { Library } from 'lucide-react'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

export default function MobileLibraryPlaceholder() {
  return (
    <div className="space-y-4 px-4 py-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-[15px]">
            <Library className="h-4 w-4" />
            Coming soon
          </CardTitle>
        </CardHeader>
        <CardContent className="text-[13px] text-muted-foreground">
          Phase M2 brings the read-only Library + Reader to mobile, with touch
          highlights and per-paragraph notes synced back to your laptop.
        </CardContent>
      </Card>
    </div>
  )
}
