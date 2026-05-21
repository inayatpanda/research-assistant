/**
 * Phase M1.4 — Mobile settings.
 *
 * Re-uses the same Settings cards as the desktop page but lays them out
 * in a single scrollable column (no responsive grid). Wraps each card
 * in the same container layout the existing settings UI uses, so we
 * don't have to duplicate any of the configuration components.
 */
import { useQuery } from '@tanstack/react-query'

import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ExportCard } from '@/components/settings/ExportCard'
import { ForceDesktopCard } from '@/components/settings/ForceDesktopCard'
import { HealthLink } from '@/components/settings/HealthLink'
import { ImportDropzone } from '@/components/settings/ImportDropzone'
import { JournalTemplateCard } from '@/components/settings/JournalTemplateCard'
import { LearnLink } from '@/components/settings/LearnLink'
import { StorageCard } from '@/components/settings/StorageCard'
import { metaApi } from '@/lib/api'
import { useLastViewedProject } from '@/lib/projectContext'

import { MobileHeader } from '../components/MobileHeader'

export default function MobileSettings() {
  const { data } = useQuery({ queryKey: ['health'], queryFn: metaApi.health })
  const projectId = useLastViewedProject((s) => s.projectId)

  return (
    <div className="flex min-h-full flex-col bg-background">
      <MobileHeader title="Settings" />

      <div className="flex flex-col gap-4 px-4 py-4">
        <div>
          <div className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
            Configuration
          </div>
          <p className="mt-1 text-[12px] text-muted-foreground">
            API keys live in <code className="text-[11px] bg-muted px-1 py-0.5 rounded">.env</code>{' '}
            on the laptop hosting the backend.
          </p>
        </div>

        {/* AI providers */}
        <Card>
          <CardHeader>
            <CardTitle className="text-[15px]">AI providers</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {data &&
              Object.entries(data.ai_providers).map(([name, status]) => (
                <div
                  key={name}
                  className="flex items-center justify-between border-b last:border-b-0 border-border py-2"
                >
                  <div className="min-w-0">
                    <div className="text-[14px] font-medium capitalize">{name}</div>
                    {status.active_model && (
                      <div className="truncate text-[12px] text-muted-foreground">
                        Model: {status.active_model}
                      </div>
                    )}
                  </div>
                  <Badge
                    variant={status.ok ? 'default' : 'secondary'}
                    className={
                      status.ok
                        ? 'bg-emerald-500/15 text-emerald-700 border-emerald-500/20'
                        : ''
                    }
                  >
                    {status.ok ? 'configured' : 'no key'}
                  </Badge>
                </div>
              ))}
          </CardContent>
        </Card>

        <StorageCard health={data} />
        <ForceDesktopCard />

        {projectId && <JournalTemplateCard projectId={projectId} />}

        {projectId ? (
          <ExportCard projectId={projectId} />
        ) : (
          <Card>
            <CardHeader>
              <CardTitle className="text-[15px]">Export project</CardTitle>
            </CardHeader>
            <CardContent className="text-[12px] text-muted-foreground">
              Pick a project from the Dashboard on a wider screen to enable export.
            </CardContent>
          </Card>
        )}

        <ImportDropzone />
        <LearnLink projectId={projectId} />
        <HealthLink />
      </div>
    </div>
  )
}
