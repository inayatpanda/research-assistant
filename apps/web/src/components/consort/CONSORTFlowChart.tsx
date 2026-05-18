export function CONSORTFlowChart({ svgBase64 }: { svgBase64: string }) {
  if (!svgBase64) return null
  return (
    <img
      src={`data:image/svg+xml;base64,${svgBase64}`}
      alt="CONSORT 2010 flow diagram"
      className="w-full max-w-3xl border border-border rounded bg-white"
    />
  )
}
