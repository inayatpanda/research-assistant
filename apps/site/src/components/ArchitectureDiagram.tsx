/**
 * Pure-SVG architecture diagram.
 *
 * Shows a central Mac (the "always-on" laptop that holds the data)
 * radiating dashed Tailscale lines out to an iPhone, iPad and a
 * collaborator's laptop. Drawn in SVG so it stays sharp on retina and
 * can be themed with brand CSS variables instead of bitmaps.
 *
 * Used on the homepage between feature sections and on the Sync page
 * at the top.
 */
import { brand } from '@/lib/brandTokens'

interface DeviceProps {
  x: number
  y: number
  label: string
  caption?: string
  icon: 'laptop' | 'iphone' | 'ipad'
  emphasised?: boolean
}

function Device({ x, y, label, caption, icon, emphasised }: DeviceProps) {
  const fill = emphasised ? brand.sidebar : '#FFFFFF'
  const stroke = emphasised ? brand.sidebar : '#CBD5E1'
  const fg = emphasised ? '#FAFAFA' : brand.ink
  const fgSub = emphasised ? 'rgba(250,250,250,0.7)' : brand.inkSoft

  return (
    <g transform={`translate(${x}, ${y})`}>
      {icon === 'laptop' && (
        <g>
          {/* Laptop screen */}
          <rect
            x={-50}
            y={-32}
            width={100}
            height={64}
            rx={6}
            fill={fill}
            stroke={stroke}
            strokeWidth={1.5}
          />
          {/* Laptop base / hinge */}
          <rect
            x={-60}
            y={32}
            width={120}
            height={6}
            rx={2}
            fill={stroke}
          />
          {/* Brand mark on screen */}
          <circle cx={0} cy={0} r={6} fill={emphasised ? brand.accent : brand.accentTint} />
        </g>
      )}
      {icon === 'iphone' && (
        <g>
          <rect
            x={-22}
            y={-38}
            width={44}
            height={76}
            rx={8}
            fill={fill}
            stroke={stroke}
            strokeWidth={1.5}
          />
          <rect x={-10} y={-32} width={20} height={2.5} rx={1.25} fill={stroke} />
        </g>
      )}
      {icon === 'ipad' && (
        <g>
          <rect
            x={-34}
            y={-42}
            width={68}
            height={84}
            rx={6}
            fill={fill}
            stroke={stroke}
            strokeWidth={1.5}
          />
          <rect x={-30} y={-38} width={60} height={76} rx={3} fill={emphasised ? '#1E293B' : '#F1F5F9'} />
        </g>
      )}

      <text
        x={0}
        y={icon === 'laptop' ? 62 : 56}
        textAnchor="middle"
        fontSize={13}
        fontWeight={600}
        fill={fg}
      >
        {label}
      </text>
      {caption && (
        <text
          x={0}
          y={icon === 'laptop' ? 78 : 72}
          textAnchor="middle"
          fontSize={11}
          fill={fgSub}
        >
          {caption}
        </text>
      )}
    </g>
  )
}

interface ArchitectureDiagramProps {
  className?: string
  /**
   * Show a caption strip underneath. The home page hides it (the
   * surrounding section already has its own heading); the Sync page
   * surfaces it.
   */
  showCaption?: boolean
}

export function ArchitectureDiagram({
  className = '',
  showCaption = true,
}: ArchitectureDiagramProps) {
  // Layout numbers are tuned for a 760×360 viewBox; the SVG scales.
  return (
    <div className={['w-full', className].join(' ')} data-testid="architecture-diagram">
      <svg
        viewBox="0 0 760 360"
        role="img"
        aria-labelledby="arch-title arch-desc"
        className="block h-auto w-full"
      >
        <title id="arch-title">Local-first network architecture</title>
        <desc id="arch-desc">
          Your Mac sits at the centre. Your iPhone, iPad and any collaborator
          connect to it over your private Tailscale network.
        </desc>

        {/* Dashed Tailscale lines emanating from the Mac. */}
        <g stroke={brand.accent} strokeWidth={1.5} strokeDasharray="6 6" fill="none" opacity={0.55}>
          <line x1={380} y1={180} x2={130} y2={120} />
          <line x1={380} y1={180} x2={130} y2={240} />
          <line x1={380} y1={180} x2={630} y2={120} />
          <line x1={380} y1={180} x2={630} y2={240} />
        </g>

        {/* Tailscale labels along the lines */}
        <g fontSize={10} fill={brand.accent} fontFamily="ui-monospace, monospace" opacity={0.9}>
          <text x={250} y={138} textAnchor="middle">
            tailscale
          </text>
          <text x={250} y={222} textAnchor="middle">
            tailscale
          </text>
          <text x={510} y={138} textAnchor="middle">
            tailscale
          </text>
          <text x={510} y={222} textAnchor="middle">
            tailscale
          </text>
        </g>

        {/* Centre — your Mac (emphasised) */}
        <Device
          x={380}
          y={180}
          label="Your Mac"
          caption="Always-on · your data lives here"
          icon="laptop"
          emphasised
        />

        {/* Satellites */}
        <Device x={130} y={120} label="Your iPhone" caption="Read · highlight" icon="iphone" />
        <Device x={130} y={240} label="Your iPad" caption="Ward-round notes" icon="ipad" />
        <Device x={630} y={120} label="Co-author's Mac" caption="Shared projects only" icon="laptop" />
        <Device x={630} y={240} label="Co-author's iPad" caption="Tablet review" icon="ipad" />
      </svg>

      {showCaption && (
        <p
          className="mx-auto mt-6 max-w-2xl text-center text-sm text-ink-muted"
          data-testid="architecture-caption"
        >
          Your data stays on your laptop. Other devices read over your private
          Tailscale network — no cloud broker, no proxy, no third-party
          telemetry.
        </p>
      )}
    </div>
  )
}
