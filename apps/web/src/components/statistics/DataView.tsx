import {
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
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
  Trash2,
  X,
} from 'lucide-react'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import type { Dataset } from '@/lib/api'
import { useAddTransformation } from '@/hooks/useTransformations'

const PAGE_SIZE = 50

type Row = Record<string, string> & { __row_id: string }

/**
 * Editable preview grid backed by `Dataset.variables[*].sample_values`.
 *
 * The server is source of truth: every cell-edit, row-drop, or "mark missing"
 * action appends a transformation op (mutate / filter / recode) to the
 * dataset's transformation stack. The backend re-applies the stack before
 * any analysis runs, so users never destructively edit the raw CSV.
 */
export function DataView({
  projectId,
  dataset,
}: {
  projectId: string
  dataset: Dataset
}) {
  const addTx = useAddTransformation(projectId, dataset.id)
  const variables = dataset.variables
  const columnNames = useMemo(
    () => variables.map((v) => v.name),
    [variables],
  )

  // Build pseudo-rows from sample_values. Each variable contributes up to N
  // samples; we transpose into row-of-objects shape for react-table.
  const initialRows = useMemo<Row[]>(() => {
    const maxLen = Math.max(0, ...variables.map((v) => v.sample_values.length))
    const out: Row[] = []
    for (let i = 0; i < maxLen; i += 1) {
      const row: Row = { __row_id: `r-${i}` }
      for (const v of variables) {
        row[v.name] = v.sample_values[i] ?? ''
      }
      out.push(row)
    }
    return out
  }, [variables])

  const [rows, setRows] = useState<Row[]>(initialRows)
  const [selectedRows, setSelectedRows] = useState<Set<string>>(new Set())
  const [sorting, setSorting] = useState<SortingState>([])
  const [filters, setFilters] = useState<ColumnFiltersState>([])
  const [editing, setEditing] = useState<{ rowId: string; col: string } | null>(
    null,
  )
  const editValueRef = useRef('')
  const rowsRef = useRef(rows)
  useEffect(() => {
    rowsRef.current = rows
  }, [rows])

  // Keep local rows in sync if dataset changes (different dataset selected).
  useEffect(() => {
    setRows(initialRows)
  }, [initialRows])

  const commitEdit = useCallback(() => {
    if (!editing) return
    const { rowId, col } = editing
    const oldRow = rowsRef.current.find((r) => r.__row_id === rowId)
    const oldValue = oldRow?.[col] ?? ''
    const newValue = editValueRef.current
    if (newValue === oldValue) {
      setEditing(null)
      return
    }
    setRows((prev) =>
      prev.map((r) => (r.__row_id === rowId ? { ...r, [col]: newValue } : r)),
    )
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
    const oldRow = rows.find((r) => r.__row_id === rowId)
    const oldValue = oldRow?.[col] ?? ''
    setRows((prev) =>
      prev.map((r) => (r.__row_id === rowId ? { ...r, [col]: '' } : r)),
    )
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
        op_type: 'filter',
        op_args: {
          expr: `!__row_id %in% c(${rowIds.map((r) => `"${r}"`).join(', ')})`,
          drop_row_ids: rowIds,
        },
        label: `Drop ${rowIds.length} row${rowIds.length === 1 ? '' : 's'}`,
      },
      {
        onSuccess: () => {
          setRows((prev) => prev.filter((r) => !selectedRows.has(r.__row_id)))
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
        header: () => (
          <span className="sr-only">Row selection</span>
        ),
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
          const value = row.original[name]
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
          const v = String(row.getValue(columnId) ?? '').toLowerCase()
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
    getPaginationRowModel: getPaginationRowModel(),
    initialState: { pagination: { pageSize: PAGE_SIZE } },
  })

  const pageInfo = table.getState().pagination

  return (
    <div className="space-y-2" data-testid="data-view">
      <header className="flex items-center justify-between gap-2">
        <div className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
          Data view ({rows.length} rows shown · {dataset.n_rows} total)
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
                  No rows to display.
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
          Page {pageInfo.pageIndex + 1} of {Math.max(1, table.getPageCount())}
        </div>
        <div className="flex items-center gap-1">
          <Button
            size="icon"
            variant="outline"
            className="h-7 w-7"
            onClick={() => table.previousPage()}
            disabled={!table.getCanPreviousPage()}
            aria-label="Previous page"
          >
            <ChevronLeft className="h-3.5 w-3.5" />
          </Button>
          <Button
            size="icon"
            variant="outline"
            className="h-7 w-7"
            onClick={() => table.nextPage()}
            disabled={!table.getCanNextPage()}
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
