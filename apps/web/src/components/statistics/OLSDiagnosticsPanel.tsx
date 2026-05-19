import { ChartImage } from './ChartImage'

const PANEL_LABELS: Record<string, string> = {
  residuals_vs_fitted: 'Residuals vs fitted',
  qq: 'Normal Q-Q',
  scale_location: 'Scale–location',
  residuals_vs_leverage: 'Residuals vs leverage',
}

const PANEL_ORDER = [
  'residuals_vs_fitted',
  'qq',
  'scale_location',
  'residuals_vs_leverage',
] as const

type Panels = Partial<Record<(typeof PANEL_ORDER)[number], string>>

/** Type guard for the OLS diagnostics chart payload. */
function extractPanels(chart: unknown): Panels | null {
  if (!chart || typeof chart !== 'object') return null
  const rec = chart as Record<string, unknown>
  const panels = rec.panels
  if (!panels || typeof panels !== 'object') return null
  const p = panels as Record<string, unknown>
  const out: Panels = {}
  for (const key of PANEL_ORDER) {
    const v = p[key]
    if (typeof v === 'string' && v.startsWith('data:image/png')) {
      out[key] = v
    }
  }
  return Object.keys(out).length > 0 ? out : null
}

export function OLSDiagnosticsPanel({ chart }: { chart: unknown }) {
  const panels = extractPanels(chart)
  if (!panels) return null

  return (
    <div className="space-y-2">
      <div className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
        Regression diagnostics
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {PANEL_ORDER.map((key) => {
          const dataUri = panels[key]
          if (!dataUri) return null
          return (
            <div key={key} className="space-y-1.5">
              <div className="text-[11px] font-medium text-muted-foreground">
                {PANEL_LABELS[key]}
              </div>
              <ChartImage
                chart={{ format: 'png', data_uri: dataUri, byte_size: 0 }}
                alt={PANEL_LABELS[key]}
                downloadName={`ols-${key}`}
              />
            </div>
          )
        })}
      </div>
    </div>
  )
}

export { extractPanels as __extractPanels }
