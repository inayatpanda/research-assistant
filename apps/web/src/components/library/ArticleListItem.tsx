import { motion } from 'framer-motion'
import { FileText, MoreVertical } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { absoluteFileUrl, type Article } from '@/lib/api'
import { cardEnter } from '@/lib/motion'
import { cn } from '@/lib/utils'

const STATUS_COLORS: Record<string, string> = {
  pending: 'bg-zinc-100 text-zinc-700 border-zinc-200',
  included: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  excluded: 'bg-rose-50 text-rose-700 border-rose-200',
  unsure: 'bg-amber-50 text-amber-700 border-amber-200',
}

export function ArticleListItem({
  article,
  index,
  onEdit,
  onDelete,
}: {
  article: Article
  index: number
  onEdit: (a: Article) => void
  onDelete: (a: Article) => void
}) {
  const fileUrl = absoluteFileUrl(article.file_url ?? null)

  return (
    <motion.div
      variants={cardEnter(index)}
      initial="initial"
      animate="animate"
      className="group flex items-center gap-4 p-4 rounded-lg border border-border bg-white hover:shadow-sm transition-shadow"
    >
      <div className="shrink-0 h-10 w-10 rounded-md bg-muted flex items-center justify-center text-muted-foreground">
        <FileText className="h-5 w-5" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <h4 className="text-[14px] font-semibold tracking-tight truncate">
            {article.title}
          </h4>
          <Badge
            variant="outline"
            className={cn('text-[10px] uppercase tracking-wider', STATUS_COLORS[article.review_status])}
          >
            {article.review_status}
          </Badge>
          {article.study_design && (
            <Badge variant="secondary" className="text-[10px] uppercase tracking-wider">
              {article.study_design}
            </Badge>
          )}
        </div>
        <div className="mt-1 text-[12px] text-muted-foreground truncate">
          {article.authors.length > 0
            ? article.authors.slice(0, 3).join(', ') +
              (article.authors.length > 3 ? `, +${article.authors.length - 3}` : '')
            : '— no authors —'}
        </div>
        <div className="mt-0.5 text-[12px] text-muted-foreground truncate">
          {[article.journal, article.year, article.doi].filter(Boolean).join(' · ')}
        </div>
      </div>
      <div className="flex items-center gap-1">
        {fileUrl && (
          <a
            href={fileUrl}
            target="_blank"
            rel="noopener"
            className="text-[12px] text-accent hover:underline px-2 py-1 rounded hover:bg-accent/5"
          >
            View
          </a>
        )}
        <button
          onClick={() => onEdit(article)}
          className="text-[12px] text-muted-foreground hover:text-foreground px-2 py-1 rounded hover:bg-muted"
        >
          Edit
        </button>
        <DropdownMenu>
          <DropdownMenuTrigger
            className="h-7 w-7 rounded-md hover:bg-muted inline-flex items-center justify-center text-muted-foreground"
            aria-label="More actions"
          >
            <MoreVertical className="h-4 w-4" />
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={() => onEdit(article)}>Edit metadata</DropdownMenuItem>
            <DropdownMenuItem
              onClick={() => onDelete(article)}
              className="text-rose-600"
            >
              Delete
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </motion.div>
  )
}
