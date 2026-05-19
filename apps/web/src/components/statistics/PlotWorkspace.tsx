/**
 * Phase 13.5 (MP13.5) — Plot workspace.
 *
 * Form-driven grammar-of-graphics builder. The user picks a geom, fills in the
 * columns the geom requires, hits "Render preview" to validate the spec via
 * the server (which returns a rendered PNG data URI), then "Save" to persist
 * the plot under the dataset.
 *
 * Saved plots are listed below the form, newest first. Each row has a
 * regenerate (re-render against the current transformation stack) and delete
 * action.
 */
import { BarChart3, Loader2, RefreshCw, Trash2 } from 'lucide-react'
import { useMemo, useState } from 'react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import {
  type Dataset,
  type DatasetVariable,
  type PlotCreate,
  type PlotGeom,
} from '@/lib/api'
import {
  useCreatePlot,
  useDeletePlot,
  usePlots,
  useRegeneratePlot,
} from '@/hooks/usePlots'

const GEOMS: { value: PlotGeom; label: string; hint: string }[] = [
  { value: 'point', label: 'Scatter (point)', hint: 'x + y, optional color/facet' },
  { value: 'line', label: 'Line', hint: 'x + y' },
  { value: 'bar', label: 'Bar', hint: 'x (and optional y)' },
  { value: 'box', label: 'Box plot', hint: 'categorical x + numeric y' },
  { value: 'violin', label: 'Violin', hint: 'categorical x + numeric y' },
  { value: 'histogram', label: 'Histogram', hint: 'numeric x' },
  { value: 'density', label: 'Density', hint: 'numeric x' },
  { value: 'heatmap', label: 'Heatmap', hint: 'x, y, value column' },
  { value: 'pair', label: 'Pair plot', hint: 'pick ≥2 numeric columns' },
]

function isNumeric(v: DatasetVariable): boolean {
  const t = v.user_type ?? v.inferred_type
  return t === 'numeric' || t === 'ordinal'
}

function isCategoricalish(v: DatasetVariable): boolean {
  const t = v.user_type ?? v.inferred_type
  return t === 'nominal' || t === 'ordinal' || t === 'event_indicator'
}

/** What channels does this geom need? */
function channelsFor(geom: PlotGeom): {
  x: boolean
  y: boolean
  color: boolean
  facet: boolean
  value: boolean
  pair: boolean
} {
  switch (geom) {
    case 'point':
    case 'line':
      return { x: true, y: true, color: true, facet: true, value: false, pair: false }
    case 'bar':
      return { x: true, y: true, color: true, facet: true, value: false, pair: false }
    case 'box':
    case 'violin':
      return { x: true, y: true, color: true, facet: true, value: false, pair: false }
    case 'histogram':
    case 'density':
      return { x: true, y: false, color: true, facet: true, value: false, pair: false }
    case 'heatmap':
      return { x: true, y: true, color: false, facet: false, value: true, pair: false }
    case 'pair':
      return { x: false, y: false, color: true, facet: false, value: false, pair: true }
  }
}

export function PlotWorkspace({
  projectId,
  dataset,
}: {
  projectId: string
  dataset: Dataset
}) {
  const { data: plots = [], isLoading } = usePlots(projectId, dataset.id)
  const create = useCreatePlot(projectId, dataset.id)
  const del = useDeletePlot(projectId, dataset.id)
  const regen = useRegeneratePlot(projectId, dataset.id)

  const [geom, setGeom] = useState<PlotGeom>('histogram')
  const [x, setX] = useState<string>('')
  const [y, setY] = useState<string>('')
  const [color, setColor] = useState<string>('')
  const [facet, setFacet] = useState<string>('')
  const [valueCol, setValueCol] = useState<string>('')
  const [pairCols, setPairCols] = useState<Set<string>>(new Set())
  const [title, setTitle] = useState<string>('')

  const channels = channelsFor(geom)
  const numericVars = useMemo(
    () => dataset.variables.filter(isNumeric),
    [dataset],
  )
  const categoricalVars = useMemo(
    () => dataset.variables.filter(isCategoricalish),
    [dataset],
  )

  function buildSpec(): PlotCreate | null {
    const body: PlotCreate = { geom, title }
    if (channels.x) {
      if (!x) return null
      body.x = x
    }
    if (channels.y) {
      // y optional for bar
      if (geom !== 'bar' && !y) return null
      if (y) body.y = y
    }
    if (channels.color && color) body.color = color
    if (channels.facet && facet) body.facet = facet
    if (channels.value) {
      if (!valueCol) return null
      body.args = { value: valueCol }
    }
    if (channels.pair) {
      if (pairCols.size < 2) return null
      body.args = { columns: Array.from(pairCols) }
    }
    return body
  }

  function handleSave() {
    const body = buildSpec()
    if (!body) {
      toast.error('Please fill the required fields for this geom.')
      return
    }
    create.mutate(body, {
      onSuccess: () => {
        toast.success('Plot saved')
        setTitle('')
      },
      onError: (e: Error) => toast.error(e.message),
    })
  }

  return (
    <div className="space-y-6" data-testid="plot-workspace">
      <div className="rounded-lg border border-border bg-white p-5 space-y-4">
        <header className="flex items-center justify-between">
          <div>
            <div className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
              Plot builder
            </div>
            <h3 className="mt-0.5 text-[14px] font-semibold">
              Grammar of graphics
            </h3>
          </div>
        </header>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div>
            <Label htmlFor="plot-geom">Geom</Label>
            <Select value={geom} onValueChange={(v) => setGeom(v as PlotGeom)}>
              <SelectTrigger id="plot-geom" data-testid="plot-geom">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {GEOMS.map((g) => (
                  <SelectItem key={g.value} value={g.value}>
                    {g.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="mt-1 text-[11px] text-muted-foreground">
              {GEOMS.find((g) => g.value === geom)?.hint}
            </p>
          </div>

          <div>
            <Label htmlFor="plot-title">Title (optional)</Label>
            <Input
              id="plot-title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Length-of-stay by approach"
            />
          </div>

          {channels.x && (
            <ColPicker
              id="plot-x"
              label="X"
              value={x}
              onChange={setX}
              options={
                geom === 'box' || geom === 'violin' || geom === 'bar'
                  ? categoricalVars.concat(
                      numericVars.filter(
                        (n) => !categoricalVars.find((c) => c.id === n.id),
                      ),
                    )
                  : dataset.variables
              }
            />
          )}

          {channels.y && (
            <ColPicker
              id="plot-y"
              label={geom === 'bar' ? 'Y (optional)' : 'Y'}
              value={y}
              onChange={setY}
              options={
                geom === 'box' || geom === 'violin'
                  ? numericVars
                  : dataset.variables
              }
              allowEmpty={geom === 'bar'}
            />
          )}

          {channels.value && (
            <ColPicker
              id="plot-value"
              label="Value column"
              value={valueCol}
              onChange={setValueCol}
              options={numericVars}
            />
          )}

          {channels.color && (
            <ColPicker
              id="plot-color"
              label="Color (optional)"
              value={color}
              onChange={setColor}
              options={dataset.variables}
              allowEmpty
            />
          )}

          {channels.facet && (
            <ColPicker
              id="plot-facet"
              label="Facet (optional)"
              value={facet}
              onChange={setFacet}
              options={dataset.variables}
              allowEmpty
            />
          )}

          {channels.pair && (
            <div className="md:col-span-2">
              <Label>Columns (numeric, pick 2+)</Label>
              <div className="mt-1 flex flex-wrap gap-2">
                {numericVars.map((v) => {
                  const checked = pairCols.has(v.name)
                  return (
                    <button
                      key={v.id}
                      type="button"
                      onClick={() => {
                        setPairCols((prev) => {
                          const next = new Set(prev)
                          if (next.has(v.name)) next.delete(v.name)
                          else next.add(v.name)
                          return next
                        })
                      }}
                      className={`text-[12px] px-2.5 py-1 rounded-md border transition-colors ${
                        checked
                          ? 'bg-accent text-white border-accent'
                          : 'bg-white border-border text-muted-foreground hover:border-accent/60'
                      }`}
                    >
                      {v.name}
                    </button>
                  )
                })}
              </div>
            </div>
          )}
        </div>

        <div className="flex items-center justify-end gap-2">
          <Button
            onClick={handleSave}
            disabled={create.isPending}
            className="bg-accent hover:bg-accent-hover text-white"
            data-testid="plot-save"
          >
            {create.isPending && (
              <Loader2 className="h-4 w-4 mr-1.5 animate-spin" />
            )}
            Render + save
          </Button>
        </div>
      </div>

      <section className="space-y-3">
        <div className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
          Saved plots ({plots.length})
        </div>
        {isLoading ? (
          <Skeleton className="h-[200px] w-full rounded-lg" />
        ) : plots.length === 0 ? (
          <div className="rounded-lg border border-dashed border-border bg-white/40 p-8 text-center">
            <BarChart3 className="h-6 w-6 mx-auto text-muted-foreground" />
            <div className="mt-2 text-[13px] font-medium">No plots yet</div>
            <div className="mt-1 text-[12px] text-muted-foreground">
              Use the builder above to create a plot.
            </div>
          </div>
        ) : (
          <ul className="space-y-3">
            {plots.map((p) => (
              <li
                key={p.id}
                className="rounded-lg border border-border bg-white p-4 space-y-2"
                data-testid={`plot-row-${p.id}`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="text-[13px] font-medium truncate">
                      {p.title || `${String(p.spec.geom)} plot`}
                    </div>
                    <div className="text-[11px] text-muted-foreground">
                      {String(p.spec.geom)}
                      {p.spec.x ? ` · x=${String(p.spec.x)}` : ''}
                      {p.spec.y ? ` · y=${String(p.spec.y)}` : ''}
                    </div>
                  </div>
                  <div className="flex items-center gap-1 shrink-0">
                    <Button
                      size="icon"
                      variant="ghost"
                      className="h-7 w-7"
                      onClick={() =>
                        regen.mutate(p.id, {
                          onSuccess: () => toast.success('Plot regenerated'),
                          onError: (e: Error) => toast.error(e.message),
                        })
                      }
                      aria-label="Regenerate"
                    >
                      <RefreshCw className="h-4 w-4 text-muted-foreground" />
                    </Button>
                    <Button
                      size="icon"
                      variant="ghost"
                      className="h-7 w-7"
                      onClick={() => {
                        if (confirm('Delete this plot?')) {
                          del.mutate(p.id, {
                            onSuccess: () => toast.success('Plot deleted'),
                            onError: (e: Error) => toast.error(e.message),
                          })
                        }
                      }}
                      aria-label="Delete plot"
                    >
                      <Trash2 className="h-4 w-4 text-muted-foreground" />
                    </Button>
                  </div>
                </div>
                {p.png_data_uri && (
                  <img
                    src={p.png_data_uri}
                    alt={p.title || `${String(p.spec.geom)} plot`}
                    className="w-full rounded border border-border"
                  />
                )}
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  )
}

function ColPicker({
  id,
  label,
  value,
  onChange,
  options,
  allowEmpty,
}: {
  id: string
  label: string
  value: string
  onChange: (v: string) => void
  options: DatasetVariable[]
  allowEmpty?: boolean
}) {
  return (
    <div>
      <Label htmlFor={id}>{label}</Label>
      <Select
        value={value || '__none__'}
        onValueChange={(v) => onChange(v === '__none__' ? '' : v)}
      >
        <SelectTrigger id={id} data-testid={id}>
          <SelectValue placeholder="Pick a column" />
        </SelectTrigger>
        <SelectContent>
          {allowEmpty && <SelectItem value="__none__">— none —</SelectItem>}
          {options.map((v) => (
            <SelectItem key={v.id} value={v.name}>
              {v.name}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  )
}
