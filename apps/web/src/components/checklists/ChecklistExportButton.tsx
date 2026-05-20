import { Download } from 'lucide-react'
import { useState } from 'react'

import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { checklistsApi } from '@/lib/api'

export type ChecklistExportButtonProps = {
  projectId: string
  runId: string
  filenameBase: string
}

/**
 * MP20 — Export the completed checklist as PDF or DOCX.
 *
 * Uses the URL.createObjectURL pattern to trigger a download from a Blob
 * (works without any third-party file-saver dep).
 */
export function ChecklistExportButton({
  projectId,
  runId,
  filenameBase,
}: ChecklistExportButtonProps) {
  const [busy, setBusy] = useState<'pdf' | 'docx' | null>(null)

  const onPick = async (format: 'pdf' | 'docx') => {
    setBusy(format)
    try {
      const blob = await checklistsApi.exportRun(projectId, runId, format)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${filenameBase}.${format}`
      a.click()
      URL.revokeObjectURL(url)
    } finally {
      setBusy(null)
    }
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          size="sm"
          variant="outline"
          data-testid="checklist-export-button"
          disabled={busy !== null}
        >
          <Download className="mr-1 h-4 w-4" />
          {busy ? 'Exporting…' : 'Export'}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem onClick={() => onPick('pdf')}>
          Export as PDF
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => onPick('docx')}>
          Export as DOCX
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
