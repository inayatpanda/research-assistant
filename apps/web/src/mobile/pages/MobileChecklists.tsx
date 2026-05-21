/**
 * Phase M5.2 — Mobile reporting-checklists mini-app (list page).
 *
 * Lives at ``/m/checklists``. Renders:
 *   - Page title "Reporting checklists".
 *   - Project picker chip (same shape as MobileStatsUpload).
 *   - List of available checklist types, grouped into rows. Tapping a
 *     row navigates to ``/m/checklists/:catalogueKey``.
 *   - Existing runs at the bottom — tapping a run jumps to the detail
 *     page with that specific run.
 *
 * Item count chips show "X/N" of items marked pass on the most recent
 * run for the project (if any).
 */
import { useQuery } from '@tanstack/react-query'
import { ChevronDown, ChevronRight, ClipboardList } from 'lucide-react'
import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { checklistsApi, projectsApi } from '@/lib/api'
import { useLastViewedProject } from '@/lib/projectContext'
import { cn } from '@/lib/utils'

import { BottomSheet } from '../components/BottomSheet'
import { MobileEmpty } from '../components/MobileEmpty'

export default function MobileChecklists() {
  const navigate = useNavigate()
  const lastProjectId = useLastViewedProject((s) => s.projectId)
  const setLastProject = useLastViewedProject((s) => s.set)
  const [picker, setPicker] = useState(false)

  const projects = useQuery({
    queryKey: ['projects', 'list'],
    queryFn: () => projectsApi.list(),
    staleTime: 60_000,
  })

  const activeProjectId = useMemo(() => {
    const list = projects.data ?? []
    if (list.length === 0) return null
    const valid = lastProjectId && list.some((p) => p.id === lastProjectId)
    return valid ? lastProjectId : list[0]?.id ?? null
  }, [projects.data, lastProjectId])

  const activeProject = useMemo(
    () => projects.data?.find((p) => p.id === activeProjectId) ?? null,
    [projects.data, activeProjectId],
  )

  const catalogue = useQuery({
    queryKey: ['mchecklists', 'catalogue'],
    queryFn: () => checklistsApi.listCatalogue(),
    staleTime: 5 * 60 * 1000,
  })

  const runs = useQuery({
    queryKey: ['mchecklists', 'runs', activeProjectId],
    queryFn: () => checklistsApi.listRuns(activeProjectId!),
    enabled: !!activeProjectId,
    staleTime: 30_000,
  })

  function onPickProject(pid: string) {
    setLastProject(pid)
    setPicker(false)
  }

  return (
    <div className="flex min-h-full flex-col bg-background pb-12">
      <div className="px-4 pt-4 pb-1">
        <h2 className="text-[20px] font-semibold tracking-tight">
          Reporting checklists
        </h2>
      </div>

      {/* Project picker chip */}
      <div className="flex items-center justify-between gap-2 px-4 pt-1 pb-3">
        <button
          type="button"
          onClick={() => setPicker(true)}
          data-testid="mchecklists-project-trigger"
          className="flex min-w-0 items-center gap-1 text-left"
        >
          <div className="min-w-0">
            <div className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
              Project
            </div>
            <div className="flex min-w-0 items-center gap-1">
              <h2 className="truncate text-[16px] font-semibold tracking-tight">
                {activeProject?.title ?? 'No project'}
              </h2>
              <ChevronDown className="h-4 w-4 shrink-0 text-muted-foreground" />
            </div>
          </div>
        </button>
      </div>

      {/* Catalogue types */}
      <div className="px-3">
        <div className="px-1 pb-2 text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
          Choose a checklist
        </div>
        {catalogue.isLoading && (
          <div
            data-testid="mchecklists-catalogue-loading"
            className="py-6 text-center text-[12px] text-muted-foreground"
          >
            Loading catalogue…
          </div>
        )}
        {!catalogue.isLoading && (catalogue.data ?? []).length > 0 && (
          <div
            data-testid="mchecklists-catalogue-list"
            className="divide-y divide-border rounded-xl border border-border bg-card"
          >
            {(catalogue.data ?? []).map((c) => (
              <button
                key={c.key}
                type="button"
                data-testid={`mchecklists-type-${c.key}`}
                onClick={() => navigate(`/m/checklists/${c.key}`)}
                className="flex w-full items-center gap-3 px-4 py-3 text-left transition-colors active:bg-muted/60 hover:bg-muted/40"
              >
                <ClipboardList
                  className="h-5 w-5 shrink-0 text-muted-foreground"
                  strokeWidth={1.75}
                />
                <div className="min-w-0 flex-1">
                  <div className="truncate text-[14px] font-medium leading-tight">
                    {c.name}
                  </div>
                  <div className="mt-0.5 text-[12px] text-muted-foreground">
                    {c.item_count} items · v{c.version}
                  </div>
                </div>
                <ChevronRight className="h-4 w-4 text-muted-foreground" />
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Active runs */}
      <div className="mt-6 px-3">
        <div className="px-1 pb-2 text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
          Runs in this project
        </div>
        {runs.isLoading && (
          <div
            data-testid="mchecklists-runs-loading"
            className="py-6 text-center text-[12px] text-muted-foreground"
          >
            Loading runs…
          </div>
        )}
        {!runs.isLoading && (runs.data ?? []).length === 0 && (
          <MobileEmpty
            title="No runs yet"
            subtitle="Pick a checklist above to start one."
            testId="mchecklists-runs-empty"
          />
        )}
        {!runs.isLoading && (runs.data ?? []).length > 0 && (
          <div
            data-testid="mchecklists-runs-list"
            className="divide-y divide-border rounded-xl border border-border bg-card"
          >
            {(runs.data ?? []).map((r) => (
              <button
                key={r.id}
                type="button"
                data-testid={`mchecklists-run-${r.id}`}
                onClick={() =>
                  navigate(
                    `/m/checklists/${r.checklist_key}?run=${r.id}`,
                  )
                }
                className="flex w-full items-center gap-3 px-4 py-3 text-left transition-colors active:bg-muted/60 hover:bg-muted/40"
              >
                <div className="min-w-0 flex-1">
                  <div className="truncate text-[14px] font-medium leading-tight">
                    {r.title}
                  </div>
                  <div className="mt-0.5 text-[12px] text-muted-foreground">
                    {Math.round(r.overall_compliance_pct)}% complete ·{' '}
                    {r.item_count} items
                  </div>
                </div>
                <ChevronRight className="h-4 w-4 text-muted-foreground" />
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Project picker sheet */}
      <BottomSheet
        open={picker}
        onClose={() => setPicker(false)}
        title="Choose a project"
        snapPoints={['60%']}
      >
        {(projects.data ?? []).length === 0 && (
          <div className="py-6 text-center text-[13px] text-muted-foreground">
            No projects found. Create one on the desktop app first.
          </div>
        )}
        {(projects.data ?? []).map((p) => (
          <button
            key={p.id}
            type="button"
            data-testid={`mchecklists-project-${p.id}`}
            onClick={() => onPickProject(p.id)}
            className={cn(
              'flex w-full items-center justify-between border-b border-border last:border-b-0 py-3 text-left',
              p.id === activeProjectId && 'font-semibold',
            )}
          >
            <div className="min-w-0">
              <div className="truncate text-[14px]">{p.title}</div>
              <div className="mt-0.5 truncate text-[11px] text-muted-foreground">
                {p.study_type}
              </div>
            </div>
            <ChevronRight className="h-4 w-4 text-muted-foreground" />
          </button>
        ))}
      </BottomSheet>
    </div>
  )
}
