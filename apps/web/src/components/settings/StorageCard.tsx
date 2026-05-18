import { Cloud, HardDrive } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import type { Health } from '@/lib/api'

export function StorageCard({ health }: { health: Health | undefined }) {
  const backend = health?.storage_backend ?? 'unknown'
  const isLocal = backend === 'local'

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-[15px]">Storage</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex items-start gap-3">
          {isLocal ? (
            <HardDrive className="h-4 w-4 mt-[2px] text-muted-foreground shrink-0" />
          ) : (
            <Cloud className="h-4 w-4 mt-[2px] text-muted-foreground shrink-0" />
          )}
          <div className="min-w-0 flex-1">
            <div className="text-[13px] font-medium capitalize">
              {isLocal ? 'Local filesystem' : backend}
            </div>
            <div className="text-[12px] text-muted-foreground mt-0.5">
              Backend identifier:{' '}
              <span className="font-mono text-foreground">{backend}</span>
            </div>
            {isLocal && (
              <div className="text-[12px] text-muted-foreground mt-1">
                Articles, datasets and the SQLite database live next to the API process
                under <code className="font-mono text-foreground bg-muted px-1 py-0.5 rounded">DATA_DIR</code>.
              </div>
            )}
          </div>
        </div>
        <TooltipProvider delayDuration={150}>
          <Tooltip>
            <TooltipTrigger asChild>
              <span className="inline-flex">
                <Button variant="outline" size="sm" disabled className="h-8 text-[12px]">
                  <Cloud className="h-3 w-3 mr-1" />
                  Migrate to cloud
                </Button>
              </span>
            </TooltipTrigger>
            <TooltipContent side="right" className="max-w-[260px] text-[11px]">
              Coming in a future release — will migrate the local SQLite database and file
              storage to your chosen cloud provider (Supabase planned).
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </CardContent>
    </Card>
  )
}
