import {
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getSortedRowModel,
  useReactTable,
  type ColumnDef,
  type ColumnFiltersState,
  type SortingState,
} from '@tanstack/react-table'
import {
  ArrowUpDown,
  Check,
  ChevronLeft,
  ChevronRight,
  Filter,
  Loader2,
  Trash2,
  X,
} from 'lucide-react'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import type { Dataset } from '@/lib/api'
import { useAddTransformation } from '@/hooks/useTransformations'
import { useDatasetPreview } from '@/hooks/useDatasets'

const PAGE_SIZE = 50

type Row = Record<string, unknown> & { __row_id: string; __row_index: number }

/**
 * Editable grid backed by the server's transformation-aware data preview.
 *
 * Before stats-refine, this component synthesised pseudo-rows from
 * ``DatasetVariable.sample_values`` (≤ 5 distinct values per column),
 * which made a 120-row table appear to have only 5 rows. We now fetch
 * the actual post-transformation rows in pages via
 * ``GET /datasets/{id}/data?offset=&limit=`` and let users edit / drop
 * / mark-missing against those.
 *
 * The server remains source of truth: every cell edit, row drop, or
 * "mark missing" appends a transformation op (mutate / filter / recode)
 * to the dataset's stack. The raw CSV is never mutated.
 */
export function DataView({
  projectId,
  dataset,
}: {
  projectId: string
  dataset: Dataset
}) {
  const addTx = useAddTransformation(projectId, dataset.id)
  const [page, setPage] = useState(0)
  const offset = page * PAGE_SIZE
  const { data: preview, isLoading } = useDatasetPreview(
    projectId,
    dataset.id,
    offset,
    PAGE_SIZE,
  )

  const columnNames = useMemo<string[]>(
    () => preview?.columns ?? dataset.variables.map((v) => v.name),
    [preview, dataset.variables],
  )

  // Edits / drops / mark-missing are tracked as in-memory overlays on top
  // of the server-fetched preview. The transformation stack on the server
  // is the durable source of truth, so this overlay only needs to last
  // until the next refetch.
  const [edits, setEdits] = useState<Map<string, Record<string, string>>>(
    () => new Map(),
  )
  const [drops, setDrops] = useState<Set<string>>(new Set())
  const [selectedRows, setSelectedRows] = useState<Set<string>>(new Set())
  const [sorting, setSorting] = useState<SortingState>([])
  const [filters, setFilters] = useState<ColumnFiltersState>([])
  const [editing, setEditing] = useState<{ rowId: string; col: string } | null>(
    null,
  )
  const editValueRef = useRef('')

  const rows = useMemo<Row[]>(() => {
    if (!preview) return []
    const merged: Row[] = []
    for (const r of preview.rows) {
      const rowId = `r-${r.__row_index}`
      if (drops.has(rowId)) continue
      const overlay = edits.get(rowId)
      merged.push({
        ...r,
        ...(overlay ?? {}),
        __row_id: rowId,
      } as Row)
    }
    return merged
  }, [preview, edits, drops])

  const rowsRef = useRef(rows)
  useEffect(() => {
    rowsRef.current = rows
  }, [rows])

  const totalRows = preview?.total ?? dataset.n_rows
  const totalPages = Math.max(1, Math.ceil(totalRows / PAGE_SIZE))

  const commitEdit = useCallback(() => {
    if (!editing) return
    const { rowId, col } = editing
    const oldRow = rowsRef.current.find((r) => r.__row_id === rowId)
    const oldValue = String(oldRow?.[col] ?? '')
    const newValue = editValueRef.current
    if (newValue === oldValue) {
      setEditing(null)
      return
    }
    setEdits((prev) => {
      const next = new Map(prev)
      const row = next.get(rowId) ?? {}
      next.set(rowId, { ...row, [col]: newValue })
      return next
    })
    addTx.mutate(
      {
        op_type: 'mutate',
        op_args: {
          column: col,
          expr: newValue,
          where: { __row_id: rowId, prev: oldValue },
        },
        label: `Edit ${col}`,
      },
      {
        onSuccess: () => toast.success(`Edit queued for ${col}`),
        onError: (e: Error) => toast.error(e.message),
      },
    )
    setEditing(null)
  }, [editing, addTx])

  const cancelEdit = useCallback(() => {
    setEditing(null)
  }, [])

  function markMissing(rowId: string, col: string) {
    const oldRow = rowsRef.current.find((r) => r.__row_id === rowId)
    const oldValue = String(oldRow?.[col] ?? '')
    setEdits((prev) => {
      const next = new Map(prev)
      const row = next.get(rowId) ?? {}
      next.set(rowId, { ...row, [col]: '' })
      return next
    })
    addTx.mutate(
      {
        op_type: 'recode',
        op_args: {
          column: col,
          mapping: { [oldValue]: '' },
          where: { __row_id: rowId },
        },
        label: `Mark ${col} missing`,
      },
      {
        onError: (e: Error) => toast.error(e.message),
      },
    )
  }

  function dropSelected() {
    if (selectedRows.size === 0) return
    const rowIds = Array.from(selectedRows)
    addTx.mutate(
      {
        // MP-stats-refine — backend learnt a dedicated drop_rows op. Pass
        // both the structured `indices` (row numbers parsed out of the
        // r-N ids) and the raw ids so the server can validate against
        // either shape.
        op_type: 'drop_rows',
        op_args: {
          indices: rowIds
            .map((r) => Number(r.replace(/^r-/, '')))
            .filter((n) => Number.isFinite(n)),
          drop_row_ids: rowIds,
        },
        label: `Drop ${rowIds.length} row${rowIds.length === 1 ? '' : 's'}`,
      },
      {
        onSuccess: () => {
          setDrops((prev) => {
            const next = new Set(prev)
            rowIds.forEach((id) => next.add(id))
            return next
          })
          setSelectedRows(new Set())
          toast.success(`Dropped ${rowIds.length} row(s)`)
        },
        onError: (e: Error) => toast.error(e.message),
      },
    )
  }

  function toggleRow(rowId: string) {
    setSelectedRows((prev) => {
      const next = new Set(prev)
      if (next.has(rowId)) next.delete(rowId)
      else next.add(rowId)
      return next
    })
  }

  const columns = useMemo<ColumnDef<Row>[]>(() => {
    const cols: ColumnDef<Row>[] = [
      {
        id: '__select',
        header: () => <span className="sr-only">Row selection</span>,
        enableSorting: false,
        enableColumnFilter: false,
        cell: ({ row }) => (
          <input
            type="checkbox"
            checked={selectedRows.has(row.original.__row_id)}
            onChange={() => toggleRow(row.original.__row_id)}
            aria-label={`Select row ${row.original.__row_id}`}
          />
        ),
      },
    ]
    for (const name of columnNames) {
      cols.push({
        id: name,
        accessorKey: name,
        header: () => <span className="font-medium">{name}</span>,
        cell: ({ row }) => {
          const rowId = row.original.__row_id
          const raw = row.original[name]
          const value =
            raw === null || raw === undefined ? '' : String(raw)
          const isEditing =
            editing && editing.rowId === rowId && editing.col === name
          if (isEditing) {
            return (
              <EditingCell
                initial={value}
                editValueRef={editValueRef}
                onCommit={commitEdit}
                onCancel={cancelEdit}
              />
            )
          }
          return (
            <div className="group flex items-center gap-1 min-h-[1.5rem]">
              <button
                type="button"
                onClick={() => {
                  editValueRef.current = value
                  setEditing({ rowId, col: name })
                }}
                className="text-left flex-1 truncate hover:bg-muted/40 rounded px-1 -mx-1 py-0.5"
                data-testid={`cell-${rowId}-${name}`}
              >
                {value || (
                  <span className="italic text-muted-foreground">(empty)</span>
                )}
              </button>
              <Button
                size="icon"
                variant="ghost"
                className="h-5 w-5 opacity-0 group-hover:opacity-100 transition-opacity"
                onClick={() => markMissing(rowId, name)}
                aria-label="Mark cell missing"
                title="Mark cell missing"
              >
                <X className="h-3 w-3 text-muted-foreground" />
              </Button>
            </div>
          )
        },
        filterFn: (row, columnId, value) => {
          if (!value) return true
          const raw = row.getValue(columnId)
          const v = String(raw ?? '').toLowerCase()
          return v.includes(String(value).toLowerCase())
        },
      })
    }
    return cols
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [columnNames, editing, selectedRows, commitEdit, cancelEdit])

  const table = useReactTable({
    data: rows,
    columns,
    state: { sorting, columnFilters: filters },
    onSortingChange: setSorting,
    onColumnFiltersChange: setFilters,
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getSortedRowModel: getSortedRowModel(),
  })

  if (isLoading && !preview) {
    return (
      <div className="space-y-2" data-testid="data-view">
        <Skeleton className="h-7 w-64" />
        <Skeleton className="h-[300px] w-full rounded-lg" />
      </div>
    )
  }

  return (
    <div className="space-y-2" data-testid="data-view">
      <header className="flex items-center justify-between gap-2">
        <div className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
          Data view ({rows.length} of {totalRows} rows
          {totalRows > rows.length ? ` · page ${page + 1}/${totalPages}` : ''})
          {isLoading ? (
            <Loader2
              data-testid="data-view-loading"
              className="inline h-3 w-3 ml-2 animate-spin"
            />
          ) : null}
        </div>
        <Button
          size="sm"
          variant="outline"
          className="h-7 text-[12px]"
          disabled={selectedRows.size === 0}
          onClick={dropSelected}
          data-testid="drop-selected"
        >
          <Trash2 className="h-3.5 w-3.5 mr-1" />
          Drop selected ({selectedRows.size})
        </Button>
      </header>

      <div className="rounded-lg border border-border bg-white overflow-auto max-h-[60vh]">
        <table className="w-full text-[12px]">
          <thead className="sticky top-0 bg-muted/40 backdrop-blur z-10">
            {table.getHeaderGroups().map((hg) => (
              <tr key={hg.id}>
                {hg.headers.map((header) => {
                  const canSort = header.column.getCanSort()
                  return (
                    <th
                      key={header.id}
                      className="text-left px-2 py-1.5 border-b border-border font-medium align-bottom"
                    >
                      <div className="flex items-center gap-1">
                        <button
                          type="button"
                          onClick={canSort ? header.column.getToggleSortingHandler() : undefined}
                          disabled={!canSort}
                          className={`text-left ${canSort ? 'hover:underline' : ''}`}
                        >
                          {flexRender(
                            header.column.columnDef.header,
                            header.getContext(),
                          )}
                        </button>
                        {canSort && (
                          <ArrowUpDown className="h-3 w-3 text-muted-foreground" />
                        )}
                      </div>
                      {header.column.getCanFilter() && (
                        <div className="mt-1 flex items-center gap-1">
                          <Filter className="h-3 w-3 text-muted-foreground" />
                          <Input
                            type="text"
                            placeholder="filter…"
                            value={(header.column.getFilterValue() ?? '') as string}
                            onChange={(e) =>
                              header.column.setFilterValue(e.target.value)
                            }
                            className="h-6 text-[11px] px-1"
                          />
                        </div>
                      )}
                    </th>
                  )
                })}
              </tr>
            ))}
          </thead>
          <tbody>
            {table.getRowModel().rows.length === 0 ? (
              <tr>
                <td
                  colSpan={columns.length}
                  className="text-center px-3 py-6 text-muted-foreground"
                >
                  {totalRows === 0
                    ? 'This dataset has no rows. Try removing filters in the transformation stack.'
                    : 'No rows on this page match the active filters.'}
                </td>
              </tr>
            ) : (
              table.getRowModel().rows.map((row) => (
                <tr
                  key={row.id}
                  className="border-b border-border last:border-0 hover:bg-muted/10"
                >
                  {row.getVisibleCells().map((cell) => (
                    <td key={cell.id} className="px-2 py-1 align-top">
                      {flexRender(
                        cell.column.columnDef.cell,
                        cell.getContext(),
                      )}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <footer className="flex items-center justify-between gap-2 text-[12px]">
        <div className="text-muted-foreground">
          Page {page + 1} of {totalPages}
        </div>
        <div className="flex items-center gap-1">
          <Button
            size="icon"
            variant="outline"
            className="h-7 w-7"
            onClick={() => setPage((p) => Math.max(0, p - 1))}
            disabled={page === 0}
            aria-label="Previous page"
          >
            <ChevronLeft className="h-3.5 w-3.5" />
          </Button>
          <Button
            size="icon"
            variant="outline"
            className="h-7 w-7"
            onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
            disabled={page >= totalPages - 1}
            aria-label="Next page"
          >
            <ChevronRight className="h-3.5 w-3.5" />
          </Button>
        </div>
      </footer>
    </div>
  )
}

function EditingCell({
  initial,
  editValueRef,
  onCommit,
  onCancel,
}: {
  initial: string
  editValueRef: React.MutableRefObject<string>
  onCommit: () => void
  onCancel: () => void
}) {
  // Self-managed (uncontrolled) so we can swap to a parent-level ref without
  // re-creating the input on every keystroke.
  const [value, setValue] = useState(initial)
  useEffect(() => {
    editValueRef.current = value
  }, [value, editValueRef])

  return (
    <div className="flex items-center gap-1">
      <Input
        autoFocus
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter') onCommit()
          if (e.key === 'Escape') onCancel()
        }}
        className="h-7 text-[12px]"
        data-testid="cell-input"
      />
      <Button
        size="icon"
        variant="ghost"
        className="h-6 w-6"
        onClick={onCommit}
        aria-label="Save edit"
      >
        <Check className="h-3 w-3 text-emerald-700" />
      </Button>
      <Button
        size="icon"
        variant="ghost"
        className="h-6 w-6"
        onClick={onCancel}
        aria-label="Cancel edit"
      >
        <X className="h-3 w-3" />
      </Button>
    </div>
  )
}
