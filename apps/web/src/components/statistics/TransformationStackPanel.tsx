import {
  DndContext,
  KeyboardSensor,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors,
  type DragEndEvent,
} from '@dnd-kit/core'
import {
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import {
  Filter,
  GripVertical,
  Layers,
  Pencil,
  Plus,
  Sigma,
  SquareSlash,
  Trash2,
} from 'lucide-react'
import { useMemo, useState } from 'react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import type {
  TransformationOpType,
  TransformationRead,
} from '@/lib/api'
import {
  useAddTransformation,
  useDeleteTransformation,
  useReorderTransformations,
  useTransformations,
} from '@/hooks/useTransformations'

const OP_LABELS: Record<TransformationOpType, string> = {
  filter: 'Filter rows',
  mutate: 'Mutate column',
  select: 'Select columns',
  recode: 'Recode values',
  drop_na: 'Drop missing',
  log_transform: 'Log transform',
  z_score: 'Z-score',
  group_summarise: 'Group + summarise',
}

const OP_ORDER: TransformationOpType[] = [
  'filter',
  'mutate',
  'select',
  'recode',
  'drop_na',
  'log_transform',
  'z_score',
  'group_summarise',
]

function OpIcon({ type }: { type: TransformationOpType }) {
  switch (type) {
    case 'filter':
    case 'drop_na':
      return <Filter className="h-3.5 w-3.5" />
    case 'mutate':
    case 'log_transform':
    case 'z_score':
      return <Pencil className="h-3.5 w-3.5" />
    case 'select':
      return <SquareSlash className="h-3.5 w-3.5" />
    case 'recode':
    case 'group_summarise':
      return <Sigma className="h-3.5 w-3.5" />
    default:
      return <Layers className="h-3.5 w-3.5" />
  }
}

/**
 * DEMO-FIX-D MEDIUM-3 — Per-op-row summary line.
 *
 * Before this fix a ``log_transform`` row just showed the input column name
 * (e.g. ``vas_pain_6m_postop``) which gave no hint of what the op did. The
 * panel now renders the output expression so the row tells the user
 * exactly what gets added to the dataset:
 *   - log_transform / z_score:  ``<new> = log(<col>)`` or ``<new> = z(<col>)``
 *   - mutate:                   ``<new> = <expr>``
 *   - filter (expr shape):      ``filter: <expr>``
 *   - filter (structured):      ``filter: <col> <op> <value>``
 *   - recode:                   ``recode <col>: a→x, b→y``
 *   - drop_na / select / etc.   unchanged
 */
function argsSummary(t: TransformationRead): string {
  const args = t.op_args ?? {}
  switch (t.op_type) {
    case 'filter': {
      if (typeof args.expr === 'string' && args.expr) {
        return `filter: ${args.expr}`
      }
      // Legacy structured shape — keep it readable.
      if (typeof args.column === 'string' && typeof args.op === 'string') {
        const val =
          args.value === undefined || args.value === null
            ? ''
            : Array.isArray(args.value)
              ? `[${(args.value as unknown[]).join(', ')}]`
              : JSON.stringify(args.value)
        return `filter: ${args.column} ${args.op} ${val}`.trim()
      }
      return 'filter'
    }
    case 'mutate': {
      const out =
        typeof args.new_column === 'string'
          ? args.new_column
          : typeof args.column === 'string'
            ? args.column
            : '?'
      const expr =
        typeof args.expression === 'string'
          ? args.expression
          : typeof args.expr === 'string'
            ? args.expr
            : '…'
      return `${out} = ${expr}`
    }
    case 'select':
      return Array.isArray(args.columns)
        ? (args.columns as string[]).join(', ')
        : ''
    case 'recode': {
      const col = typeof args.column === 'string' ? args.column : '?'
      const mapping = args.mapping
      let mapStr = ''
      if (mapping && typeof mapping === 'object' && !Array.isArray(mapping)) {
        const entries = Object.entries(mapping as Record<string, unknown>)
        mapStr = entries
          .slice(0, 4)
          .map(([k, v]) => `${k}→${String(v)}`)
          .join(', ')
        if (entries.length > 4) mapStr += `, +${entries.length - 4} more`
      }
      return mapStr ? `recode ${col}: ${mapStr}` : `recode ${col}`
    }
    case 'drop_na':
      return Array.isArray(args.columns) && (args.columns as string[]).length > 0
        ? (args.columns as string[]).join(', ')
        : '(all columns)'
    case 'log_transform': {
      const input = typeof args.column === 'string' ? args.column : '?'
      const output =
        typeof args.new_column === 'string' && args.new_column.length > 0
          ? args.new_column
          : `log_${input}`
      const base = args.base
      const fn = base === '10' ? 'log10' : base === '2' ? 'log2' : 'log'
      return `${output} = ${fn}(${input})`
    }
    case 'z_score': {
      const input = typeof args.column === 'string' ? args.column : '?'
      const output =
        typeof args.new_column === 'string' && args.new_column.length > 0
          ? args.new_column
          : `z_${input}`
      return `${output} = z(${input})`
    }
    case 'group_summarise':
      return Array.isArray(args.group_by)
        ? `by ${(args.group_by as string[]).join(', ')}`
        : ''
    default:
      return ''
  }
}

export function TransformationStackPanel({
  projectId,
  datasetId,
}: {
  projectId: string
  datasetId: string
}) {
  const { data: items = [], isLoading } = useTransformations(
    projectId,
    datasetId,
  )
  const reorder = useReorderTransformations(projectId, datasetId)
  const del = useDeleteTransformation(projectId, datasetId)
  const [addOpen, setAddOpen] = useState(false)

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 4 } }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    }),
  )

  const orderedIds = useMemo(() => items.map((i) => i.id), [items])

  function handleDragEnd(e: DragEndEvent) {
    const { active, over } = e
    if (!over || active.id === over.id) return
    const oldIndex = orderedIds.indexOf(String(active.id))
    const newIndex = orderedIds.indexOf(String(over.id))
    if (oldIndex < 0 || newIndex < 0) return
    const next = [...orderedIds]
    const [moved] = next.splice(oldIndex, 1)
    next.splice(newIndex, 0, moved)
    reorder.mutate(next, {
      onError: (e: Error) => toast.error(e.message),
    })
  }

  return (
    <div className="space-y-2">
      <header className="flex items-center justify-between gap-2">
        <div className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
          Transformations
        </div>
        <Button
          size="sm"
          variant="outline"
          className="h-7 text-[12px]"
          onClick={() => setAddOpen(true)}
          data-testid="add-transformation"
        >
          <Plus className="h-3.5 w-3.5 mr-1" />
          Add
        </Button>
      </header>

      {isLoading ? (
        <div className="text-[12px] text-muted-foreground">Loading…</div>
      ) : items.length === 0 ? (
        <div className="rounded-md border border-dashed border-border bg-muted/20 px-3 py-4 text-[12px] text-muted-foreground">
          No transformations applied — analyses use the raw uploaded data.
        </div>
      ) : (
        <DndContext
          sensors={sensors}
          collisionDetection={closestCenter}
          onDragEnd={handleDragEnd}
        >
          <SortableContext
            items={orderedIds}
            strategy={verticalListSortingStrategy}
          >
            <ul className="space-y-1.5" data-testid="transformation-stack">
              {items.map((t) => (
                <SortableRow
                  key={t.id}
                  item={t}
                  onDelete={() =>
                    del.mutate(t.id, {
                      onError: (e: Error) => toast.error(e.message),
                    })
                  }
                />
              ))}
            </ul>
          </SortableContext>
        </DndContext>
      )}

      <AddTransformationDialog
        open={addOpen}
        onOpenChange={setAddOpen}
        projectId={projectId}
        datasetId={datasetId}
      />
    </div>
  )
}

function SortableRow({
  item,
  onDelete,
}: {
  item: TransformationRead
  onDelete: () => void
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id: item.id })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  }

  const label = item.label || OP_LABELS[item.op_type]
  const summary = argsSummary(item)

  return (
    <li
      ref={setNodeRef}
      style={style}
      className="flex items-center gap-2 rounded-md border border-border bg-white px-2 py-1.5"
    >
      <button
        type="button"
        aria-label="Drag to reorder"
        className="text-muted-foreground hover:text-foreground p-1 cursor-grab"
        {...attributes}
        {...listeners}
      >
        <GripVertical className="h-3.5 w-3.5" />
      </button>
      <div className="text-muted-foreground">
        <OpIcon type={item.op_type} />
      </div>
      <div className="min-w-0 flex-1">
        <div className="text-[12px] font-medium truncate">{label}</div>
        {summary && (
          <div className="text-[11px] text-muted-foreground truncate font-mono">
            {summary}
          </div>
        )}
      </div>
      <Button
        size="icon"
        variant="ghost"
        className="h-6 w-6"
        onClick={onDelete}
        aria-label="Delete transformation"
      >
        <Trash2 className="h-3.5 w-3.5 text-muted-foreground" />
      </Button>
    </li>
  )
}

function AddTransformationDialog({
  open,
  onOpenChange,
  projectId,
  datasetId,
}: {
  open: boolean
  onOpenChange: (o: boolean) => void
  projectId: string
  datasetId: string
}) {
  const add = useAddTransformation(projectId, datasetId)
  const [opType, setOpType] = useState<TransformationOpType>('filter')
  const [label, setLabel] = useState('')
  // Generic arg fields (best-effort UI for the most common shapes).
  const [argA, setArgA] = useState('')
  const [argB, setArgB] = useState('')

  function reset() {
    setOpType('filter')
    setLabel('')
    setArgA('')
    setArgB('')
  }

  function buildArgs(): Record<string, unknown> {
    switch (opType) {
      case 'filter':
        return { expr: argA }
      case 'mutate':
        return { column: argA, expr: argB }
      case 'select':
        return {
          columns: argA
            .split(',')
            .map((s) => s.trim())
            .filter((s) => s.length > 0),
        }
      case 'recode':
        return { column: argA, mapping: parseMapping(argB) }
      case 'drop_na':
        return {
          columns: argA
            .split(',')
            .map((s) => s.trim())
            .filter((s) => s.length > 0),
        }
      case 'log_transform':
      case 'z_score':
        return { column: argA }
      case 'group_summarise':
        return {
          group_by: argA
            .split(',')
            .map((s) => s.trim())
            .filter((s) => s.length > 0),
        }
      default:
        return {}
    }
  }

  function onSubmit() {
    add.mutate(
      { op_type: opType, op_args: buildArgs(), label },
      {
        onSuccess: () => {
          onOpenChange(false)
          reset()
        },
        onError: (e: Error) => toast.error(e.message),
      },
    )
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(o) => {
        onOpenChange(o)
        if (!o) reset()
      }}
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Add transformation</DialogTitle>
        </DialogHeader>
        <div className="space-y-3">
          <div className="space-y-1.5">
            <Label htmlFor="op-type">Operation</Label>
            <Select
              value={opType}
              onValueChange={(v) => setOpType(v as TransformationOpType)}
            >
              <SelectTrigger id="op-type">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {OP_ORDER.map((k) => (
                  <SelectItem key={k} value={k}>
                    {OP_LABELS[k]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <ArgFields
            opType={opType}
            argA={argA}
            argB={argB}
            setArgA={setArgA}
            setArgB={setArgB}
          />
          <div className="space-y-1.5">
            <Label htmlFor="op-label">Label (optional)</Label>
            <Input
              id="op-label"
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              placeholder="e.g. Drop hhs_6w NA"
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            onClick={onSubmit}
            disabled={add.isPending}
            className="bg-accent hover:bg-accent-hover text-white"
          >
            Add transformation
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function ArgFields({
  opType,
  argA,
  argB,
  setArgA,
  setArgB,
}: {
  opType: TransformationOpType
  argA: string
  argB: string
  setArgA: (v: string) => void
  setArgB: (v: string) => void
}) {
  const labelA: Record<TransformationOpType, string> = {
    filter: 'Expression',
    mutate: 'Column name',
    select: 'Columns (comma-separated)',
    recode: 'Column',
    drop_na: 'Columns (blank = all)',
    log_transform: 'Column',
    z_score: 'Column',
    group_summarise: 'Group by (comma-separated)',
  }
  const labelB: Partial<Record<TransformationOpType, string>> = {
    mutate: 'Expression',
    recode: 'Mapping (old=new, …)',
  }
  return (
    <>
      <div className="space-y-1.5">
        <Label htmlFor="op-arg-a">{labelA[opType]}</Label>
        <Input
          id="op-arg-a"
          value={argA}
          onChange={(e) => setArgA(e.target.value)}
          placeholder={opType === 'filter' ? 'age > 50' : ''}
        />
      </div>
      {labelB[opType] && (
        <div className="space-y-1.5">
          <Label htmlFor="op-arg-b">{labelB[opType]}</Label>
          <Input
            id="op-arg-b"
            value={argB}
            onChange={(e) => setArgB(e.target.value)}
          />
        </div>
      )}
    </>
  )
}

function parseMapping(s: string): Record<string, string> {
  const out: Record<string, string> = {}
  for (const part of s.split(',')) {
    const [k, v] = part.split('=').map((x) => x.trim())
    if (k && v !== undefined) out[k] = v
  }
  return out
}
