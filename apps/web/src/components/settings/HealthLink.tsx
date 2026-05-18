import { Activity, ChevronRight } from 'lucide-react'
import { Link } from 'react-router-dom'

import { Card, CardContent } from '@/components/ui/card'

export function HealthLink() {
  return (
    <Card>
      <CardContent className="p-0">
        <Link
          to="/health"
          className="flex items-center gap-3 px-6 py-4 hover:bg-zinc-50 transition-colors"
        >
          <Activity className="h-4 w-4 text-muted-foreground shrink-0" />
          <div className="flex-1 min-w-0">
            <div className="text-[13px] font-medium">Diagnostics</div>
            <div className="text-[12px] text-muted-foreground">
              Live API status, database, AI providers and version.
            </div>
          </div>
          <ChevronRight className="h-4 w-4 text-muted-foreground" />
        </Link>
      </CardContent>
    </Card>
  )
}
