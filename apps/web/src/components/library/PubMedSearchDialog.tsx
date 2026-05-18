import { Search } from 'lucide-react'
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
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useSearchPubMed } from '@/hooks/useIngest'
import { type ArticleMetadata } from '@/lib/api'

import { ImportPreviewDialog } from './ImportPreviewDialog'

export function PubMedSearchDialog({ projectId }: { projectId: string }) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [retmax, setRetmax] = useState(20)
  const [results, setResults] = useState<ArticleMetadata[] | null>(null)
  const [previewOpen, setPreviewOpen] = useState(false)
  const search = useSearchPubMed(projectId)

  async function onSearch() {
    const q = query.trim()
    if (!q) return
    try {
      const items = await search.mutateAsync({ query: q, retmax })
      if (items.length === 0) {
        toast.info('No PubMed results for that query')
        return
      }
      setResults(items)
      setOpen(false)
      setPreviewOpen(true)
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'PubMed search failed')
    }
  }

  return (
    <>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogTrigger asChild>
          <Button variant="outline">
            <Search className="h-4 w-4 mr-1" />
            Search PubMed
          </Button>
        </DialogTrigger>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Search PubMed</DialogTitle>
            <DialogDescription>
              Query the NCBI E-utilities for article metadata. Records are
              previewed before they're added to your library.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <div>
              <Label htmlFor="pubmed-q">Query</Label>
              <Input
                id="pubmed-q"
                placeholder="e.g. anterior approach total hip arthroplasty"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault()
                    void onSearch()
                  }
                }}
                disabled={search.isPending}
              />
            </div>
            <div>
              <Label htmlFor="pubmed-retmax">Max results</Label>
              <Select
                value={String(retmax)}
                onValueChange={(v) => setRetmax(Number(v))}
              >
                <SelectTrigger id="pubmed-retmax">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="5">5</SelectItem>
                  <SelectItem value="10">10</SelectItem>
                  <SelectItem value="20">20</SelectItem>
                  <SelectItem value="50">50</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="ghost"
              onClick={() => setOpen(false)}
              disabled={search.isPending}
            >
              Cancel
            </Button>
            <Button
              onClick={() => void onSearch()}
              disabled={search.isPending || !query.trim()}
            >
              {search.isPending ? 'Searching…' : 'Search'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {results !== null && (
        <ImportPreviewDialog
          projectId={projectId}
          open={previewOpen}
          items={results}
          onOpenChange={(o) => {
            setPreviewOpen(o)
            if (!o) setResults(null)
          }}
        />
      )}
    </>
  )
}
