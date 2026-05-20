import { useState } from 'react'

import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from '@/components/ui/resizable'
import { ChecklistRunDrawer } from '@/components/checklists/ChecklistRunDrawer'
import { ChecklistRunsList } from '@/components/checklists/ChecklistRunsList'
import { ChecklistsList } from '@/components/checklists/ChecklistsList'
import { useProjectId } from '@/lib/projectContext'

/**
 * MP20 — Interactive reporting-checklist workspace.
 *
 * Layout (left → right):
 *   ChecklistsList — catalogue of available reporting guidelines
 *   ChecklistRunsList — runs in progress on this project
 *   ChecklistRunDrawer — editable view of the selected run (or empty state)
 */
export default function ChecklistsPage() {
  const projectId = useProjectId()
  return <ChecklistsInner projectId={projectId} />
}

function ChecklistsInner({ projectId }: { projectId: string }) {
  const [activeRunId, setActiveRunId] = useState<string | null>(null)

  return (
    <div className="h-[calc(100vh-4rem)] p-3" data-testid="checklists-page-shell">
      <ResizablePanelGroup
        direction="horizontal"
        autoSaveId="divider-widths-checklists"
      >
        <ResizablePanel defaultSize={22} minSize={15} maxSize={35}>
          <div className="h-full overflow-hidden rounded-md border bg-card">
            <ChecklistsList
              projectId={projectId}
              onRunCreated={(run) => setActiveRunId(run.id)}
            />
          </div>
        </ResizablePanel>
        <ResizableHandle withHandle />
        <ResizablePanel defaultSize={26} minSize={18} maxSize={40}>
          <div className="h-full overflow-hidden rounded-md border bg-card">
            <ChecklistRunsList
              projectId={projectId}
              activeRunId={activeRunId}
              onSelect={setActiveRunId}
            />
          </div>
        </ResizablePanel>
        <ResizableHandle withHandle />
        <ResizablePanel defaultSize={52} minSize={30}>
          <div className="h-full overflow-hidden rounded-md border bg-card">
            {activeRunId ? (
              <ChecklistRunDrawer projectId={projectId} runId={activeRunId} />
            ) : (
              <div
                className="flex h-full items-center justify-center p-6 text-center text-sm text-muted-foreground"
                data-testid="checklists-empty-state"
              >
                Select a run from the middle pane, or start a new checklist on
                the left.
              </div>
            )}
          </div>
        </ResizablePanel>
      </ResizablePanelGroup>
    </div>
  )
}
