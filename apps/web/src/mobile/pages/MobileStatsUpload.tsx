/**
 * Phase M4.1 — Page 1 of the mobile Statistics wizard.
 *
 * Mounted at ``/m/stats`` (the bottom-tab entry point). Two distinct
 * surfaces live here:
 *
 *   1. A project selector chip at the top, reusing the persisted
 *      ``useLastViewedProject`` store so the user lands on the same
 *      project they last touched.
 *   2. An upload card with a tap-to-pick (and drag-drop on devices that
 *      support it) zone. CSV / XLSX / XLS up to 25 MiB.
 *   3. A list of existing datasets in the active project. Tapping a
 *      dataset row jumps straight to Step 2 with that dataset selected,
 *      so a returning user doesn't have to re-upload anything.
 *
 * Successful upload → navigate to step 2 (`/m/stats/:datasetId/preview`).
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  ChevronDown,
  ChevronRight,
  Database,
  FileSpreadsheet,
  Loader2,
  Upload,
} from 'lucide-react'
import { useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'

import {
  datasetsApi,
  projectsApi,
  type Dataset,
} from '@/lib/api'
import { useLastViewedProject } from '@/lib/projectContext'
import { cn } from '@/lib/utils'

import { BottomSheet } from '../components/BottomSheet'
import { MobileEmpty } from '../components/MobileEmpty'

const MAX_BYTES = 25 * 1024 * 1024 // 25 MiB
const ACCEPT = '.csv,.xlsx,.xls'

export default function MobileStatsUpload() {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const lastProjectId = useLastViewedProject((s) => s.projectId)
  const setLastProject = useLastViewedProject((s) => s.set)
  const fileInputRef = useRef<HTMLInputElement | null>(null)
  const [picker, setPicker] = useState(false)
  const [dragOver, setDragOver] = useState(false)

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

  const datasets = useQuery({
    queryKey: ['mstats', 'datasets', activeProjectId],
    queryFn: () => datasetsApi.list(activeProjectId!),
    enabled: !!activeProjectId,
    staleTime: 30_000,
  })

  const upload = useMutation({
    mutationFn: async (file: File) => {
      if (!activeProjectId) throw new Error('Pick a project first')
      if (file.size > MAX_BYTES) throw new Error('File is larger than 25 MiB')
      return datasetsApi.upload(activeProjectId, file)
    },
    onSuccess: (ds) => {
      qc.invalidateQueries({ queryKey: ['mstats', 'datasets', activeProjectId] })
      toast.success('Dataset uploaded')
      navigate(`/m/stats/${ds.id}/preview`)
    },
    onError: (err) => {
      toast.error(err instanceof Error ? err.message : 'Upload failed')
    },
  })

  function onPickProject(pid: string) {
    setLastProject(pid)
    setPicker(false)
  }

  function onFileChosen(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file) return
    upload.mutate(file)
  }

  function onDrop(e: React.DragEvent<HTMLDivElement>) {
    e.preventDefault()
    setDragOver(false)
    const file = e.dataTransfer?.files?.[0]
    if (!file) return
    upload.mutate(file)
  }

  return (
    <div className="flex min-h-full flex-col bg-background pb-12">
      {/* Project selector — same shape as MobileLibrary so the user
          recognises it. */}
      <div className="flex items-center justify-between gap-2 px-4 pt-4 pb-3">
        <button
          type="button"
          onClick={() => setPicker(true)}
          data-testid="mstats-project-trigger"
          className="flex min-w-0 items-center gap-1 text-left"
        >
          <div className="min-w-0">
            <div className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
              Project
            </div>
            <div className="flex min-w-0 items-center gap-1">
              <h2 className="truncate text-[18px] font-semibold tracking-tight">
                {activeProject?.title ?? 'No project'}
              </h2>
              <ChevronDown className="h-4 w-4 shrink-0 text-muted-foreground" />
            </div>
          </div>
        </button>
      </div>

      {/* Upload card */}
      <div className="px-3">
        <div
          data-testid="mstats-upload-card"
          onClick={() => fileInputRef.current?.click()}
          onDragOver={(e) => {
            e.preventDefault()
            setDragOver(true)
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={onDrop}
          className={cn(
            'flex cursor-pointer flex-col items-center justify-center gap-2 rounded-2xl border-2 border-dashed bg-card px-4 py-10 text-center',
            'transition-colors',
            dragOver
              ? 'border-primary bg-primary/5'
              : 'border-border hover:bg-muted/40 active:bg-muted/60',
          )}
        >
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 text-primary">
            {upload.isPending ? (
              <Loader2 className="h-5 w-5 animate-spin" />
            ) : (
              <Upload className="h-5 w-5" />
            )}
          </div>
          <div className="text-[15px] font-semibold tracking-tight">
            Upload your dataset
          </div>
          <div className="max-w-[260px] text-[12px] text-muted-foreground">
            Tap to pick a .csv, .xlsx or .xls file. Drag-and-drop also
            works on devices that support it. Max 25 MiB.
          </div>
        </div>
        <input
          ref={fileInputRef}
          type="file"
          accept={ACCEPT}
          className="hidden"
          data-testid="mstats-file-input"
          onChange={onFileChosen}
          disabled={!activeProjectId || upload.isPending}
        />
      </div>

      {/* Existing datasets list */}
      <div className="mt-6 px-3">
        <div className="px-1 pb-2 text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
          Existing datasets
        </div>
        {datasets.isLoading && (
          <div
            data-testid="mstats-datasets-loading"
            className="py-6 text-center text-[12px] text-muted-foreground"
          >
            Loading datasets…
          </div>
        )}
        {!datasets.isLoading && (datasets.data ?? []).length === 0 && (
          <MobileEmpty
            icon={Database}
            title="No datasets yet"
            subtitle="Upload one above to start an analysis."
            testId="mstats-datasets-empty"
          />
        )}
        {!datasets.isLoading && (datasets.data ?? []).length > 0 && (
          <div
            data-testid="mstats-datasets-list"
            className="divide-y divide-border rounded-xl border border-border bg-card"
          >
            {(datasets.data ?? []).map((ds) => (
              <DatasetRow
                key={ds.id}
                dataset={ds}
                onOpen={() => navigate(`/m/stats/${ds.id}/preview`)}
              />
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
            data-testid={`mstats-project-${p.id}`}
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

function DatasetRow({
  dataset,
  onOpen,
}: {
  dataset: Dataset
  onOpen: () => void
}) {
  return (
    <button
      type="button"
      data-testid={`mstats-ds-row-${dataset.id}`}
      onClick={onOpen}
      className="flex w-full items-center gap-3 px-4 py-3 text-left transition-colors active:bg-muted/60 hover:bg-muted/40"
    >
      <FileSpreadsheet
        className="h-5 w-5 shrink-0 text-muted-foreground"
        strokeWidth={1.75}
      />
      <div className="min-w-0 flex-1">
        <div className="truncate text-[14px] font-medium leading-tight">
          {dataset.filename}
        </div>
        <div className="mt-0.5 text-[12px] text-muted-foreground">
          {dataset.n_rows.toLocaleString()} rows · {dataset.n_columns} cols
        </div>
      </div>
      <ChevronRight className="h-4 w-4 text-muted-foreground" />
    </button>
  )
}
