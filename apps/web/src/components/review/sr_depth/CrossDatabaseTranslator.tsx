/**
 * CrossDatabaseTranslator (MP19) — pick a source strategy, pick a target
 * DB, get the translated query and a warnings list. Optional persist
 * stores the translated query as a child strategy.
 */
import { Loader2, Save } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import type { TranslateResponse, TranslationTarget } from '@/lib/api'
import {
  useSearchStrategies,
  useTranslateSearchStrategy,
} from '@/hooks/useSearchStrategies'

const TARGETS: { value: TranslationTarget; label: string }[] = [
  { value: 'embase', label: 'Embase' },
  { value: 'cochrane', label: 'Cochrane' },
  { value: 'wos', label: 'Web of Science' },
]

export function CrossDatabaseTranslator({ projectId }: { projectId: string }) {
  const list = useSearchStrategies(projectId)
  const translate = useTranslateSearchStrategy(projectId)
  const [sourceId, setSourceId] = useState('')
  const [target, setTarget] = useState<TranslationTarget>('embase')
  const [result, setResult] = useState<TranslateResponse | null>(null)

  const pubmedStrategies = (list.data ?? []).filter(
    (s) => s.database === 'PubMed',
  )

  const run = async (persist: boolean) => {
    if (!sourceId) {
      toast.error('Pick a PubMed strategy to translate from.')
      return
    }
    try {
      const r = await translate.mutateAsync({ id: sourceId, to: target, persist })
      setResult(r)
      if (persist) toast.success('Saved as a new strategy.')
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Translation failed.')
    }
  }

  return (
    <div className="space-y-4" data-testid="cross-db-translator">
      <div className="grid grid-cols-2 gap-3">
        <div>
          <Label htmlFor="tr-src">Source PubMed strategy</Label>
          <select
            id="tr-src"
            className="mt-1 w-full rounded border border-border bg-background px-2 py-1.5 text-sm"
            value={sourceId}
            onChange={(e) => setSourceId(e.target.value)}
            data-testid="tr-source"
          >
            <option value="">Select…</option>
            {pubmedStrategies.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </div>
        <div>
          <Label htmlFor="tr-tgt">Target database</Label>
          <select
            id="tr-tgt"
            className="mt-1 w-full rounded border border-border bg-background px-2 py-1.5 text-sm"
            value={target}
            onChange={(e) => setTarget(e.target.value as TranslationTarget)}
            data-testid="tr-target"
          >
            {TARGETS.map((t) => (
              <option key={t.value} value={t.value}>
                {t.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="flex gap-2">
        <Button onClick={() => run(false)} disabled={translate.isPending}>
          {translate.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin mr-1" />
          ) : null}
          Translate
        </Button>
        <Button
          variant="outline"
          onClick={() => run(true)}
          disabled={translate.isPending || !sourceId}
        >
          <Save className="h-4 w-4 mr-1" />
          Save as strategy
        </Button>
      </div>

      {result && (
        <div className="space-y-3" data-testid="tr-result">
          <div>
            <Label>Translated query</Label>
            <pre
              className="mt-1 whitespace-pre-wrap break-words rounded border border-border bg-muted/50 p-3 text-[12px] font-mono"
              data-testid="tr-output"
            >
              {result.translated_query}
            </pre>
          </div>
          {result.warnings.length > 0 && (
            <div data-testid="tr-warnings">
              <Label>Warnings ({result.warnings.length})</Label>
              <ul className="mt-1 space-y-1 text-[12px] text-amber-700 dark:text-amber-300">
                {result.warnings.map((w, i) => (
                  <li key={i}>• {w}</li>
                ))}
              </ul>
              <p className="mt-2 text-[11px] text-muted-foreground">
                Review before running on the target database.
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
