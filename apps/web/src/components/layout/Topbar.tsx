import { useQuery } from '@tanstack/react-query'
import { CircleDot } from 'lucide-react'

import { metaApi } from '@/lib/api'
import { cn } from '@/lib/utils'

import { MobileNav } from './MobileNav'

export function Topbar() {
  const { data, isError } = useQuery({
    queryKey: ['health'],
    queryFn: metaApi.health,
    refetchInterval: 30_000,
  })

  const ok = !isError && data?.status === 'ok'
  const degraded = !isError && data?.status === 'degraded'

  return (
    <header className="h-14 shrink-0 border-b border-border bg-white flex items-center justify-between px-3 md:px-5">
      <div className="flex items-center gap-2">
        <MobileNav />
        <div className="text-[13px] text-muted-foreground">Local · ./data</div>
      </div>
      <div className="flex items-center gap-2 text-[12px] text-muted-foreground">
        <CircleDot
          className={cn(
            'h-3 w-3',
            ok && 'text-emerald-500',
            degraded && 'text-amber-500',
            !ok && !degraded && 'text-rose-500',
          )}
        />
        <span>
          {ok && 'API ready'}
          {degraded && 'API degraded'}
          {!ok && !degraded && 'API offline'}
        </span>
      </div>
    </header>
  )
}
