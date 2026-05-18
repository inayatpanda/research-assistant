import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { Activity, AlertCircle, CheckCircle2, Database, Server } from 'lucide-react'
import { Link } from 'react-router-dom'

import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { metaApi } from '@/lib/api'
import { pageEnter } from '@/lib/motion'

const REFRESH_INTERVAL_MS = 10_000

function StatusBadge({ ok }: { ok: boolean }) {
  return (
    <Badge
      variant={ok ? 'default' : 'secondary'}
      className={
        ok
          ? 'bg-emerald-500/15 text-emerald-700 border-emerald-500/20 hover:bg-emerald-500/15'
          : 'bg-rose-500/15 text-rose-700 border-rose-500/20'
      }
    >
      {ok ? (
        <CheckCircle2 className="h-3 w-3 mr-1" />
      ) : (
        <AlertCircle className="h-3 w-3 mr-1" />
      )}
      {ok ? 'OK' : 'Down'}
    </Badge>
  )
}

export default function HealthPage() {
  const { data, isLoading, isError, error, dataUpdatedAt } = useQuery({
    queryKey: ['health'],
    queryFn: metaApi.health,
    refetchInterval: REFRESH_INTERVAL_MS,
  })

  const updatedAt = dataUpdatedAt ? new Date(dataUpdatedAt).toLocaleTimeString() : '—'

  return (
    <motion.div
      variants={pageEnter}
      initial="initial"
      animate="animate"
      exit="exit"
      className="max-w-3xl mx-auto px-8 py-10 space-y-6"
    >
      <div>
        <div className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium flex items-center gap-2">
          <Activity className="h-3 w-3" />
          Diagnostics
        </div>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight">Health</h1>
        <p className="mt-1 text-[13px] text-muted-foreground">
          Live view of the API. Polled every {REFRESH_INTERVAL_MS / 1000}s. Last update:{' '}
          <span className="font-mono">{updatedAt}</span>.
          {' '}
          <Link to="/settings" className="text-accent hover:underline">
            Back to settings
          </Link>
        </p>
      </div>

      {isLoading && (
        <div className="text-[13px] text-muted-foreground">Loading health…</div>
      )}
      {isError && (
        <Card>
          <CardContent className="text-[13px] text-rose-700 py-4">
            {(error as Error)?.message ?? 'API unreachable'}
          </CardContent>
        </Card>
      )}

      {data && (
        <>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0">
              <CardTitle className="text-[15px] flex items-center gap-2">
                <Server className="h-4 w-4 text-muted-foreground" />
                API
              </CardTitle>
              <StatusBadge ok={data.status === 'ok'} />
            </CardHeader>
            <CardContent className="space-y-1 text-[13px]">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Status</span>
                <span className="font-mono">{data.status}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Version</span>
                <span className="font-mono">{data.version}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Storage backend</span>
                <span className="font-mono">{data.storage_backend}</span>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0">
              <CardTitle className="text-[15px] flex items-center gap-2">
                <Database className="h-4 w-4 text-muted-foreground" />
                Database
              </CardTitle>
              <StatusBadge ok={data.db_ok} />
            </CardHeader>
            <CardContent className="text-[13px] text-muted-foreground">
              {data.db_ok
                ? 'SQLite reachable; queries returning successfully.'
                : 'Database is unreachable. The API will return errors for most operations.'}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-[15px]">AI providers</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {Object.entries(data.ai_providers).map(([name, status]) => (
                <div
                  key={name}
                  className="flex items-center justify-between border-b last:border-b-0 border-border py-2"
                >
                  <div className="min-w-0">
                    <div className="text-[13px] font-medium capitalize">{name}</div>
                    {status.active_model && (
                      <div className="text-[11px] font-mono text-muted-foreground">
                        {status.active_model}
                      </div>
                    )}
                    {status.reason && (
                      <div className="text-[11px] text-muted-foreground">{status.reason}</div>
                    )}
                  </div>
                  <StatusBadge ok={status.ok} />
                </div>
              ))}
            </CardContent>
          </Card>
        </>
      )}
    </motion.div>
  )
}
