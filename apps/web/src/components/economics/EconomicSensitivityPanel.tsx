import { useState } from 'react'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useRunEconomicSensitivity } from '@/hooks/useEconomicAnalyses'
import type { EconomicAnalysis } from '@/lib/api'

export interface EconomicSensitivityPanelProps {
  projectId: string
  analysis: EconomicAnalysis
}

type Kind = 'psa' | 'dsa' | 'scenario'

/**
 * MP18 — Toggles between PSA / DSA / scenario sensitivity flavours.
 *
 * For brevity the form is intentionally minimal: PSA + DSA both take
 * lows/highs (with normal distributions assumed for PSA); scenarios are
 * entered as JSON. Power users get the full surface via direct API calls;
 * the dialog is enough to drive the typical CRAFFT-style workflow.
 */
export function EconomicSensitivityPanel({
  projectId,
  analysis,
}: EconomicSensitivityPanelProps) {
  const [kind, setKind] = useState<Kind>('dsa')
  const [costLow, setCostLow] = useState('0')
  const [costHigh, setCostHigh] = useState('1000')
  const [qalyLow, setQalyLow] = useState('0')
  const [qalyHigh, setQalyHigh] = useState('0.2')
  const [scenarioJson, setScenarioJson] = useState(
    '[{"name":"Best case","overrides":{"mean_qaly_diff":0.15}}]',
  )
  const mutation = useRunEconomicSensitivity(projectId, analysis.id)

  const handleRun = () => {
    if (kind === 'dsa') {
      mutation.mutate({
        kind,
        body: {
          parameter_ranges: {
            mean_cost_diff: { low: Number(costLow), high: Number(costHigh) },
            mean_qaly_diff: { low: Number(qalyLow), high: Number(qalyHigh) },
          },
        },
      })
    } else if (kind === 'psa') {
      mutation.mutate({
        kind,
        body: {
          parameter_distributions: {
            mean_cost_diff: {
              dist: 'normal',
              mean: analysis.result?.mean_cost_diff ?? 0,
              sd: 100,
            },
            mean_qaly_diff: {
              dist: 'normal',
              mean: analysis.result?.mean_qaly_diff ?? 0.05,
              sd: 0.02,
            },
          },
          n_psa: 1000,
          seed: 42,
        },
      })
    } else {
      try {
        const scenarios = JSON.parse(scenarioJson) as Array<{
          name: string
          overrides: Record<string, number>
        }>
        mutation.mutate({ kind, body: { scenarios } })
      } catch (_err) {
        mutation.mutate({
          kind,
          body: { scenarios: [{ name: 'Invalid JSON', overrides: {} }] },
        })
      }
    }
  }

  return (
    <Card data-testid="economic-sensitivity-panel">
      <CardHeader>
        <CardTitle>Sensitivity analysis</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div>
          <Label htmlFor="sens-kind">Type</Label>
          <Select value={kind} onValueChange={(v) => setKind(v as Kind)}>
            <SelectTrigger id="sens-kind"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="psa">PSA (probabilistic)</SelectItem>
              <SelectItem value="dsa">DSA (one-way deterministic)</SelectItem>
              <SelectItem value="scenario">Named scenarios</SelectItem>
            </SelectContent>
          </Select>
        </div>
        {kind === 'dsa' && (
          <div className="grid grid-cols-2 gap-2">
            <div>
              <Label htmlFor="dsa-cost-low">dCost low</Label>
              <Input
                id="dsa-cost-low"
                value={costLow}
                onChange={(e) => setCostLow(e.target.value)}
              />
            </div>
            <div>
              <Label htmlFor="dsa-cost-high">dCost high</Label>
              <Input
                id="dsa-cost-high"
                value={costHigh}
                onChange={(e) => setCostHigh(e.target.value)}
              />
            </div>
            <div>
              <Label htmlFor="dsa-qaly-low">dQALY low</Label>
              <Input
                id="dsa-qaly-low"
                value={qalyLow}
                onChange={(e) => setQalyLow(e.target.value)}
              />
            </div>
            <div>
              <Label htmlFor="dsa-qaly-high">dQALY high</Label>
              <Input
                id="dsa-qaly-high"
                value={qalyHigh}
                onChange={(e) => setQalyHigh(e.target.value)}
              />
            </div>
          </div>
        )}
        {kind === 'psa' && (
          <p className="text-sm text-muted-foreground">
            PSA draws 1000 samples of mean_cost_diff and mean_qaly_diff from
            normal distributions centred on the point estimate with SDs of
            {' '}{analysis.result?.mean_cost_diff ? '100' : 'n/a'} and{' '}
            0.02 respectively.
          </p>
        )}
        {kind === 'scenario' && (
          <div>
            <Label htmlFor="sens-scenario-json">Scenarios (JSON)</Label>
            <textarea
              id="sens-scenario-json"
              className="w-full h-32 rounded-md border border-border bg-background p-2 text-sm font-mono"
              value={scenarioJson}
              onChange={(e) => setScenarioJson(e.target.value)}
            />
          </div>
        )}
        <div>
          <Button
            type="button"
            onClick={handleRun}
            disabled={mutation.isPending || !analysis.result}
          >
            {mutation.isPending ? 'Running…' : `Run ${kind.toUpperCase()}`}
          </Button>
        </div>
        {analysis.result?.sensitivity && (
          <pre className="rounded-md border border-border bg-muted/30 p-2 text-xs overflow-auto max-h-64">
            {JSON.stringify(analysis.result.sensitivity, null, 2)}
          </pre>
        )}
      </CardContent>
    </Card>
  )
}
