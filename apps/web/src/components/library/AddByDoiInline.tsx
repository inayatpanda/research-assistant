import { Search } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useLookupDoi } from '@/hooks/useIngest'
import { type ArticleMetadata } from '@/lib/api'

export function AddByDoiInline({
  projectId,
  onResult,
}: {
  projectId: string
  onResult: (meta: ArticleMetadata) => void
}) {
  const [doi, setDoi] = useState('')
  const lookup = useLookupDoi(projectId)

  async function onLookup() {
    const trimmed = doi.trim()
    if (!trimmed) return
    try {
      const meta = await lookup.mutateAsync(trimmed)
      onResult(meta)
      setDoi('')
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'DOI lookup failed'
      toast.error(msg)
    }
  }

  return (
    <div className="rounded-lg border border-border bg-white/40 p-4">
      <Label htmlFor="doi-input" className="text-[12px] font-medium">
        Add by DOI
      </Label>
      <div className="mt-2 flex items-center gap-2">
        <Input
          id="doi-input"
          placeholder="10.1056/NEJMoa2110345 or https://doi.org/…"
          value={doi}
          onChange={(e) => setDoi(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault()
              void onLookup()
            }
          }}
          disabled={lookup.isPending}
        />
        <Button
          onClick={() => void onLookup()}
          disabled={lookup.isPending || !doi.trim()}
        >
          <Search className="h-4 w-4 mr-1" />
          {lookup.isPending ? 'Looking…' : 'Look up'}
        </Button>
      </div>
    </div>
  )
}
