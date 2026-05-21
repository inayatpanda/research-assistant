/**
 * Phase M0.5 — "More" tab placeholder.
 *
 * M1 will host account / settings / sign-out / backend URL here, and
 * M5 will add the mini-apps (Economics, Checklists, Submission).
 */
import { Menu } from 'lucide-react'
import { Link } from 'react-router-dom'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

export default function MobileMorePlaceholder() {
  return (
    <div className="space-y-4 px-4 py-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-[15px]">
            <Menu className="h-4 w-4" />
            Coming soon
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-[13px] text-muted-foreground">
          <p>
            Phase M1 and M5 will populate this tab with account settings,
            backend configuration, economics + checklists + submission
            mini-apps, and a sign-out action.
          </p>
          <Link
            to="/m/setup"
            className="inline-flex items-center text-[13px] font-medium text-primary underline-offset-2 hover:underline"
          >
            Change backend URL
          </Link>
        </CardContent>
      </Card>
    </div>
  )
}
