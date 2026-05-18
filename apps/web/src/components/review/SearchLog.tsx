import { Loader2, Plus, Send, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
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
import { Textarea } from '@/components/ui/textarea'
import {
  DatabaseNameSchema,
  type DatabaseName,
  type SearchRecord,
} from '@/lib/api'
import {
  useCreateSearch,
  useDeleteSearch,
  usePushSearch,
  useSearchRecords,
} from '@/hooks/useReviews'

const DATABASES: DatabaseName[] = DatabaseNameSchema.options

export function SearchLog({ projectId }: { projectId: string }) {
  const { data: rows = [], isLoading } = useSearchRecords(projectId)
  const push = usePushSearch(projectId)
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)

  return (
    <div className="space-y-4">
      <header className="flex items-center justify-between">
        <div>
          <h3 className="text-[15px] font-semibold tracking-tight">Search log</h3>
          <div className="text-[12px] text-muted-foreground">
            Record each database query for transparency and reproducibility.
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() =>
              push.mutate(undefined, {
                onSuccess: () => {
                  toast.success('Pushed to Methodology')
                  navigate('/manuscript?section=Methodology')
                },
                onError: (e: Error) => toast.error(e.message),
              })
            }
            disabled={push.isPending || rows.length === 0}
          >
            {push.isPending ? (
              <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />
            ) : (
              <Send className="h-3.5 w-3.5 mr-1.5" />
            )}
            Push to Methodology
          </Button>
          <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
              <Button size="sm" className="bg-accent hover:bg-accent-hover text-white">
                <Plus className="h-3.5 w-3.5 mr-1.5" />
                Add search
              </Button>
            </DialogTrigger>
            <DialogContent>
              <AddSearchForm projectId={projectId} onDone={() => setOpen(false)} />
            </DialogContent>
          </Dialog>
        </div>
      </header>

      <div className="rounded-lg border border-border bg-white overflow-hidden">
        <table className="w-full text-[13px]">
          <thead className="bg-muted/30 text-[11px] uppercase tracking-wider text-muted-foreground">
            <tr>
              <th className="text-left px-3 py-2 font-medium">Database</th>
              <th className="text-left px-3 py-2 font-medium">Date</th>
              <th className="text-left px-3 py-2 font-medium">Query</th>
              <th className="text-right px-3 py-2 font-medium">n results</th>
              <th className="text-right px-3 py-2 font-medium w-[44px]"></th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr>
                <td colSpan={5} className="px-3 py-6 text-center text-muted-foreground">
                  Loading…
                </td>
              </tr>
            ) : rows.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-3 py-6 text-center text-muted-foreground">
                  No search records yet. Click <span className="font-medium">Add search</span> to log one.
                </td>
              </tr>
            ) : (
              rows.map((r) => <SearchRow key={r.id} projectId={projectId} row={r} />)
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function SearchRow({ projectId, row }: { projectId: string; row: SearchRecord }) {
  const del = useDeleteSearch(projectId)
  return (
    <tr className="border-t border-border">
      <td className="px-3 py-2 font-medium">{row.database_name}</td>
      <td className="px-3 py-2 tabular-nums text-muted-foreground">
        {new Date(row.date_searched).toISOString().slice(0, 10)}
      </td>
      <td className="px-3 py-2 font-mono text-[12px] max-w-[420px] truncate" title={row.query_string}>
        {row.query_string}
      </td>
      <td className="px-3 py-2 text-right tabular-nums">{row.n_results}</td>
      <td className="px-3 py-2 text-right">
        <Button
          size="icon"
          variant="ghost"
          className="h-7 w-7"
          aria-label="Delete search record"
          onClick={() => {
            if (!confirm('Delete this search record?')) return
            del.mutate(row.id, {
              onError: (e: Error) => toast.error(e.message),
            })
          }}
        >
          <Trash2 className="h-3.5 w-3.5 text-muted-foreground" />
        </Button>
      </td>
    </tr>
  )
}

function AddSearchForm({
  projectId,
  onDone,
}: {
  projectId: string
  onDone: () => void
}) {
  const create = useCreateSearch(projectId)
  const [database, setDatabase] = useState<DatabaseName>('PubMed')
  const [query, setQuery] = useState('')
  const [date, setDate] = useState(() => new Date().toISOString().slice(0, 10))
  const [n, setN] = useState('0')
  const [notes, setNotes] = useState('')

  function submit(e: React.FormEvent) {
    e.preventDefault()
    const nResults = Number(n)
    if (!Number.isFinite(nResults) || nResults < 0) {
      toast.error('n results must be a non-negative number')
      return
    }
    if (!query.trim()) {
      toast.error('Query is required')
      return
    }
    create.mutate(
      {
        database_name: database,
        query_string: query.trim(),
        date_searched: new Date(date + 'T00:00:00Z').toISOString(),
        n_results: nResults,
        notes: notes.trim() || null,
      },
      {
        onSuccess: () => {
          toast.success('Search added')
          onDone()
        },
        onError: (e: Error) => toast.error(e.message),
      },
    )
  }

  return (
    <form onSubmit={submit} className="space-y-4">
      <DialogHeader>
        <DialogTitle>Add a search record</DialogTitle>
      </DialogHeader>
      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1">
          <Label>Database</Label>
          <Select value={database} onValueChange={(v) => setDatabase(v as DatabaseName)}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {DATABASES.map((d) => (
                <SelectItem key={d} value={d}>
                  {d}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1">
          <Label>Date searched</Label>
          <Input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
        </div>
      </div>
      <div className="space-y-1">
        <Label>Query string</Label>
        <Textarea
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="(knee arthroplasty) AND (infection OR PJI)"
          rows={3}
          className="font-mono text-[12px]"
        />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1">
          <Label>n results</Label>
          <Input
            type="number"
            min={0}
            value={n}
            onChange={(e) => setN(e.target.value)}
          />
        </div>
        <div className="space-y-1">
          <Label>Notes</Label>
          <Input value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Optional" />
        </div>
      </div>
      <div className="flex justify-end gap-2">
        <Button type="button" variant="ghost" size="sm" onClick={onDone}>
          Cancel
        </Button>
        <Button type="submit" size="sm" disabled={create.isPending} className="bg-accent hover:bg-accent-hover text-white">
          {create.isPending && <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />}
          Add
        </Button>
      </div>
    </form>
  )
}
