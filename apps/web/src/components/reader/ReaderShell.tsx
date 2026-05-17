import { motion } from 'framer-motion'
import { ArrowLeft } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'

import type { Article } from '@/lib/api'
import { pageEnter } from '@/lib/motion'

import { ArticleNotesRail } from './ArticleNotesRail'
import { PdfToolbar } from './PdfToolbar'
import { PdfViewer } from './PdfViewer'

export function ReaderShell({ article }: { article: Article }) {
  const [numPages, setNumPages] = useState(0)

  return (
    <motion.div
      variants={pageEnter}
      initial="initial"
      animate="animate"
      className="flex flex-col h-[calc(100vh-56px)]"
    >
      <div className="h-12 px-4 border-b border-border bg-white flex items-center gap-3">
        <Link
          to="/library"
          className="inline-flex items-center gap-1 text-[12px] text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Library
        </Link>
        <div className="h-4 w-px bg-border" />
        <div className="text-[13px] font-medium truncate flex-1">{article.title}</div>
        <div className="text-[11px] text-muted-foreground hidden md:block">
          {article.authors.slice(0, 2).join(', ')}
          {article.authors.length > 2 ? ` +${article.authors.length - 2}` : ''}
          {article.year ? ` · ${article.year}` : ''}
        </div>
      </div>
      <PdfToolbar numPages={numPages} />
      <div className="flex-1 min-h-0 flex">
        <PdfViewer articleId={article.id} onNumPages={setNumPages} />
        <ArticleNotesRail articleId={article.id} />
      </div>
    </motion.div>
  )
}
