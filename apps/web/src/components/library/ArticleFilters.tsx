import { Search } from 'lucide-react'
import { useEffect, useState } from 'react'

import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import type { ArticleFilters as Filters, ReviewStatus, ArticleSort } from '@/lib/api'

export function ArticleFilters({
  value,
  onChange,
}: {
  value: Filters
  onChange: (v: Filters) => void
}) {
  const [q, setQ] = useState(value.q ?? '')

  // Debounce search input (250ms)
  useEffect(() => {
    const t = setTimeout(() => {
      if ((value.q ?? '') !== q) onChange({ ...value, q: q || undefined })
    }, 250)
    return () => clearTimeout(t)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [q])

  return (
    <div className="flex flex-wrap gap-2 items-center">
      <div className="relative flex-1 min-w-[200px] max-w-md">
        <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search title…"
          className="pl-9"
        />
      </div>
      <Select
        value={value.review_status ?? 'all'}
        onValueChange={(v) =>
          onChange({ ...value, review_status: v === 'all' ? undefined : (v as ReviewStatus) })
        }
      >
        <SelectTrigger className="w-[150px]">
          <SelectValue placeholder="All statuses" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All statuses</SelectItem>
          <SelectItem value="pending">Pending</SelectItem>
          <SelectItem value="included">Included</SelectItem>
          <SelectItem value="excluded">Excluded</SelectItem>
          <SelectItem value="unsure">Unsure</SelectItem>
        </SelectContent>
      </Select>
      <Select
        value={value.study_design ?? 'all'}
        onValueChange={(v) =>
          onChange({ ...value, study_design: v === 'all' ? undefined : v })
        }
      >
        <SelectTrigger className="w-[180px]">
          <SelectValue placeholder="All study designs" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All study designs</SelectItem>
          <SelectItem value="RCT">RCT</SelectItem>
          <SelectItem value="cohort">Cohort</SelectItem>
          <SelectItem value="case-control">Case-control</SelectItem>
          <SelectItem value="case-series">Case series</SelectItem>
          <SelectItem value="cross-sectional">Cross-sectional</SelectItem>
          <SelectItem value="systematic-review">Systematic review</SelectItem>
          <SelectItem value="meta-analysis">Meta-analysis</SelectItem>
        </SelectContent>
      </Select>
      <Select
        value={value.sort ?? 'created_desc'}
        onValueChange={(v) => onChange({ ...value, sort: v as ArticleSort })}
      >
        <SelectTrigger className="w-[160px]">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="created_desc">Newest first</SelectItem>
          <SelectItem value="year_desc">Year ↓</SelectItem>
          <SelectItem value="year_asc">Year ↑</SelectItem>
          <SelectItem value="title">Title (A–Z)</SelectItem>
        </SelectContent>
      </Select>
    </div>
  )
}
