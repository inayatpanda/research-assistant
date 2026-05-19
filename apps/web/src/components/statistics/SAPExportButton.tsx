/**
 * Phase 17 (MP17) — Streaming SAP (Statistical Analysis Plan) export button.
 *
 * Two-format download: DOCX or PDF. The download is triggered by setting
 * `window.location` to the streaming endpoint URL — same pattern the rest
 * of the app uses for protected file downloads.
 */
import { useState } from 'react'

import { sapApi } from '../../lib/api'

interface Props {
  projectId: string
  planId: string
}

export function SAPExportButton({ projectId, planId }: Props) {
  const [format, setFormat] = useState<'docx' | 'pdf'>('docx')
  return (
    <div data-testid="sap-export">
      <label>
        Format
        <select value={format} onChange={(e) => setFormat(e.target.value as never)}>
          <option value="docx">DOCX</option>
          <option value="pdf">PDF</option>
        </select>
      </label>
      <a
        href={sapApi.exportUrl(projectId, planId, format)}
        download
        data-testid="sap-download-link"
      >
        Download SAP
      </a>
    </div>
  )
}

export default SAPExportButton
