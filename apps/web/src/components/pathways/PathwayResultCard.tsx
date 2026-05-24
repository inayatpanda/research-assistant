import { useState } from 'react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import {
  pathwaysApi,
  type PathwayKey,
  type PathwayResponse,
} from '@/lib/api'

export type PathwayResultCardProps = {
  projectId: string
  datasetId: string
  response: PathwayResponse
  /** When set, render this content next to the prose (e.g. summary table). */
  children?: React.ReactNode
}

export function PathwayResultCard({
  projectId,
  datasetId,
  response,
  children,
}: PathwayResultCardProps) {
  const [methods, setMethods] = useState(response.prose.methods)
  const [results, setResults] = useState(response.prose.results)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [target, setTarget] = useState<'methods' | 'results' | 'both'>('both')
  const [pushing, setPushing] = useState(false)

  const handlePush = async () => {
    setPushing(true)
    try {
      await pathwaysApi.push(projectId, datasetId, {
        pathway: response.pathway as PathwayKey,
        target,
        methods: methods.trim(),
        results: results.trim(),
      })
      toast.success(
        target === 'both'
          ? 'Pushed to Methodology and Results'
          : `Pushed to ${target === 'methods' ? 'Methodology' : 'Results'}`,
      )
      setDialogOpen(false)
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Push failed'
      toast.error(msg)
    } finally {
      setPushing(false)
    }
  }

  return (
    <section
      className="rounded-lg border border-border bg-white p-5 space-y-4"
      data-testid={`pathway-result-${response.pathway}`}
    >
      <header className="flex items-start justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold">Pathway result</h3>
          <p className="text-xs text-muted-foreground">
            {response.pathway.replace('-', ' ')}
          </p>
        </div>
        <Button
          size="sm"
          onClick={() => setDialogOpen(true)}
          data-testid="pathway-push-btn"
        >
          Push to manuscript
        </Button>
      </header>

      {children}

      <div className="space-y-3">
        <div>
          <Label
            htmlFor={`prose-methods-${response.pathway}`}
            className="text-xs font-medium text-muted-foreground"
          >
            Methods (editable)
          </Label>
          <Textarea
            id={`prose-methods-${response.pathway}`}
            value={methods}
            onChange={(e) => setMethods(e.target.value)}
            rows={6}
            className="font-serif text-sm leading-relaxed"
          />
        </div>
        <div>
          <Label
            htmlFor={`prose-results-${response.pathway}`}
            className="text-xs font-medium text-muted-foreground"
          >
            Results (editable)
          </Label>
          <Textarea
            id={`prose-results-${response.pathway}`}
            value={results}
            onChange={(e) => setResults(e.target.value)}
            rows={6}
            className="font-serif text-sm leading-relaxed"
          />
        </div>
      </div>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Push to manuscript</DialogTitle>
            <DialogDescription>
              Append the prose into your project&apos;s manuscript sections.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-2">
            <Label className="text-xs font-medium text-muted-foreground">
              Insert into
            </Label>
            <div className="grid grid-cols-3 gap-2">
              {(['methods', 'results', 'both'] as const).map((t) => (
                <button
                  key={t}
                  type="button"
                  onClick={() => setTarget(t)}
                  className={
                    'rounded border px-3 py-2 text-sm capitalize transition-colors ' +
                    (target === t
                      ? 'border-primary bg-primary/10'
                      : 'border-border hover:bg-muted')
                  }
                >
                  {t === 'methods' ? 'Methodology' : t === 'results' ? 'Results' : 'Both'}
                </button>
              ))}
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setDialogOpen(false)}
              disabled={pushing}
            >
              Cancel
            </Button>
            <Button onClick={handlePush} disabled={pushing}>
              {pushing ? 'Pushing...' : 'Confirm push'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </section>
  )
}
