/**
 * Phase 12 — Submission package dialog.
 *
 * Triggered from the Manuscript header (or Settings). Optional snapshot
 * dropdown lets the user pin the manuscript content to a saved version
 * — when omitted, the live state is bundled.
 */
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
  DialogTrigger,
} from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useSnapshots } from '@/hooks/useSnapshots'
import { exportApi } from '@/lib/api'

const LIVE_VALUE = '__live__'

export function SubmissionPackageDialog({
  projectId,
  trigger,
}: {
  projectId: string
  trigger?: React.ReactNode
}) {
  const [open, setOpen] = useState(false)
  const [selected, setSelected] = useState<string>(LIVE_VALUE)
  const [downloading, setDownloading] = useState(false)
  const { data: snapshots = [] } = useSnapshots(open ? projectId : null)

  async function handleDownload() {
    setDownloading(true)
    try {
      const filename = await exportApi.downloadSubmissionPackage(
        projectId,
        selected === LIVE_VALUE ? undefined : selected,
      )
      toast.success(`Downloaded ${filename}`)
      setOpen(false)
    } catch (e) {
      toast.error((e as Error).message || 'Could not download package')
    } finally {
      setDownloading(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        {trigger ?? (
          <Button variant="outline" data-testid="submission-package-button">
            Submission package…
          </Button>
        )}
      </DialogTrigger>
      <DialogContent data-testid="submission-package-dialog">
        <DialogHeader>
          <DialogTitle>Download submission package</DialogTitle>
          <DialogDescription>
            Bundles the manuscript, every figure, every table, the cover
            letter, and any drafted reviewer responses into a single zip.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-3">
          <div>
            <Label htmlFor="submission-snapshot">Manuscript version</Label>
            <Select value={selected} onValueChange={setSelected}>
              <SelectTrigger
                id="submission-snapshot"
                data-testid="submission-snapshot-trigger"
              >
                <SelectValue placeholder="Live (current draft)" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={LIVE_VALUE}>Live (current draft)</SelectItem>
                {snapshots.map((s) => (
                  <SelectItem key={s.id} value={s.id}>
                    {s.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
        <DialogFooter>
          <Button variant="ghost" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button
            onClick={handleDownload}
            disabled={downloading}
            data-testid="submission-download-button"
          >
            {downloading ? 'Downloading…' : 'Download submission package'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
