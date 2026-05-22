import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'

import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ExportCard } from '@/components/settings/ExportCard'
import { ForceDesktopCard } from '@/components/settings/ForceDesktopCard'
import { HealthLink } from '@/components/settings/HealthLink'
import { ImportDropzone } from '@/components/settings/ImportDropzone'
import { JournalTemplateCard } from '@/components/settings/JournalTemplateCard'
import { LearnLink } from '@/components/settings/LearnLink'
import { LicenseStatusCard } from '@/components/settings/LicenseStatusCard'
import { StorageCard } from '@/components/settings/StorageCard'
import { metaApi } from '@/lib/api'
import { pageEnter } from '@/lib/motion'
import { useLastViewedProject } from '@/lib/projectContext'

export default function SettingsPage() {
  const { data } = useQuery({ queryKey: ['health'], queryFn: metaApi.health })
  // Settings is a global page (no projectId in URL), so we use the
  // last-viewed project for context — same UX as before MP12.5.
  const projectId = useLastViewedProject((s) => s.projectId)

  return (
    <motion.div
      variants={pageEnter}
      initial="initial"
      animate="animate"
      exit="exit"
      className="max-w-screen-2xl mx-auto px-8 py-10 space-y-6"
    >
      <div>
        <div className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
          Settings
        </div>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight">Configuration</h1>
        <p className="mt-1 text-[13px] text-muted-foreground">
          API keys live in <code className="text-[12px] bg-muted px-1 py-0.5 rounded">.env</code>{' '}
          at the project root. Restart the API to apply changes.
        </p>
      </div>

      <div
        data-testid="settings-grid"
        className="grid grid-cols-1 2xl:grid-cols-2 4xl:grid-cols-3 gap-6 auto-rows-min items-start"
      >
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
                <div>
                  <div className="text-[14px] font-medium capitalize">{name}</div>
                  {status.active_model && (
                    <div className="text-[12px] text-muted-foreground">
                      Model: {status.active_model}
                    </div>
                  )}
                  {status.reason && (
                    <div className="text-[12px] text-muted-foreground">{status.reason}</div>
                  )}
                </div>
                <Badge
                  variant={status.ok ? 'default' : 'secondary'}
                  className={
                    status.ok
                      ? 'bg-emerald-500/15 text-emerald-700 border-emerald-500/20 hover:bg-emerald-500/15'
                      : ''
                  }
                >
                  {status.ok ? 'configured' : 'no key'}
                </Badge>
              </div>
            ))}
        </CardContent>
      </Card>

      {/* Phase L1b — licence status, devices, upgrade. */}
      <LicenseStatusCard />

      <StorageCard health={data} />

      {/* Phase M0.6 — let power users force the desktop UI on iPads / small browsers. */}
      <ForceDesktopCard />

      {projectId && <JournalTemplateCard projectId={projectId} />}

      {projectId ? (
        <ExportCard projectId={projectId} />
      ) : (
        <Card>
          <CardHeader>
            <CardTitle className="text-[15px]">Export project</CardTitle>
          </CardHeader>
          <CardContent className="text-[13px] text-muted-foreground">
            Pick a project from the Dashboard to enable manuscript export.
          </CardContent>
        </Card>
      )}

      <ImportDropzone />

      <LearnLink projectId={projectId} />

      <HealthLink />
      </div>
    </motion.div>
  )
}
