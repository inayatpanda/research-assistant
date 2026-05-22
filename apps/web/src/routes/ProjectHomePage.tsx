/**
 * MP12.5 — project home page.
 *
 * Lands the user at `/projects/:projectId` and acts as the launchpad
 * for the per-project modules. We grid out a tile for each module
 * (Library, Reader, Compile, Manuscript, Statistics, Review, CONSORT,
 * Submission) and show a tiny stat next to each — read straight from
 * the existing list endpoints, no new backend needed.
 *
 * Stats are fetched as independent useQuery() calls so a slow endpoint
 * never blocks the rest of the page. Each tile renders with a 0 default
 * while its query is in flight or fails.
 */
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import {
  BarChart3,
  BookOpen,
  CheckSquare,
  ClipboardList,
  Coins,
  FileImage,
  FileText,
  History,
  Image as ImageIcon,
  Layers,
  Library as LibraryIcon,
  MessageSquare,
  MessageSquareWarning,
  PenLine,
  Send,
  Workflow,
} from 'lucide-react'
import type { ComponentType } from 'react'
import { Link } from 'react-router-dom'

import { MembersPanel } from '@/components/auth/MembersPanel'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import {
  articlesApi,
  datasetsApi,
  manuscriptApi,
  type ManuscriptSectionName,
} from '@/lib/api'
import { pageEnter } from '@/lib/motion'
import { useProject, useProjectId } from '@/lib/projectContext'

const MANUSCRIPT_SECTIONS: ManuscriptSectionName[] = [
  'Abstract',
  'Introduction',
  'Methodology',
  'Results',
  'Discussion',
  'Conclusion',
]

type ModuleCardSpec = {
  to: string
  label: string
  icon: ComponentType<{ className?: string }>
  stat: (s: ProjectStats) => string
  blurb: string
}

type ProjectStats = {
  articleCount: number
  datasetCount: number
  manuscriptWords: number
}

const MODULES: ModuleCardSpec[] = [
  {
    to: 'library',
    label: 'Library',
    icon: LibraryIcon,
    stat: (s) =>
      s.articleCount === 1 ? '1 article' : `${s.articleCount} articles`,
    blurb: 'PDFs, DOIs, PubMed, RIS/BibTeX',
  },
  {
    to: 'reader',
    label: 'Reader',
    icon: FileText,
    stat: () => 'Open an article',
    blurb: 'Highlight passages in colour',
  },
  {
    to: 'compile',
    label: 'Compile',
    icon: Layers,
    stat: () => 'Group by colour',
    blurb: 'Aggregate highlights into draft sentences',
  },
  {
    to: 'manuscript',
    label: 'Manuscript',
    icon: PenLine,
    stat: (s) => `${s.manuscriptWords.toLocaleString()} words`,
    blurb: 'IMRaD editor with citations & bibliography',
  },
  {
    to: 'statistics',
    label: 'Statistics',
    icon: BarChart3,
    stat: (s) =>
      s.datasetCount === 1 ? '1 dataset' : `${s.datasetCount} datasets`,
    blurb: 'Power, PSM, regression, plots',
  },
  {
    // Fix-E2E/2 — was bare 'review' which redirected to /systematic-review.
    // Now points directly at /systematic-review and the copy matches it.
    to: 'systematic-review',
    label: 'Systematic Review',
    icon: ClipboardList,
    stat: () => 'PRISMA + RoB',
    blurb: 'Screening, extraction, meta-analysis',
  },
  {
    // Fix-E2E/2 — Phase 4.6 split Peer Review into its own page; surface it
    // on the home grid so the user can reach the AI-critique tool.
    to: 'peer-review',
    label: 'Peer Review',
    icon: MessageSquareWarning,
    stat: () => 'AI critique',
    blurb: 'Editor-style peer review of your draft',
  },
  {
    to: 'consort',
    label: 'CONSORT',
    icon: Workflow,
    stat: () => 'Flow diagram',
    blurb: 'Randomised trial reporting',
  },
  {
    to: 'economics',
    label: 'Economics',
    icon: Coins,
    stat: () => 'CHEERS-ready',
    blurb: 'Cost-effectiveness, ICER, CEAC',
  },
  {
    to: 'checklists',
    label: 'Checklists',
    icon: CheckSquare,
    stat: () => 'CONSORT · PRISMA · STROBE',
    blurb: 'Reporting checklists with progress',
  },
  {
    to: 'submission',
    label: 'Submission',
    icon: Send,
    stat: () => 'Cover letter + zip',
    blurb: 'Reviewer responses & package',
  },
  {
    to: 'manuscript?section=frontmatter',
    label: 'Front matter',
    icon: FileImage,
    stat: () => 'ICMJE',
    blurb: 'Title page, authors, declarations',
  },
  {
    // Snapshots + comments live inside Manuscript; keep tiles for IA parity.
    to: 'manuscript',
    label: 'Figures',
    icon: ImageIcon,
    stat: () => 'Reorder & caption',
    blurb: 'Manage figures inside Manuscript',
  },
  {
    to: 'manuscript',
    label: 'Snapshots',
    icon: History,
    stat: () => 'Versions',
    blurb: 'Compare and restore prior drafts',
  },
  {
    to: 'manuscript',
    label: 'Comments',
    icon: MessageSquare,
    stat: () => 'Threaded notes',
    blurb: 'Per-section reviewer comments',
  },
  {
    to: 'learn',
    label: 'Learn',
    icon: BookOpen,
    stat: () => 'Reference library',
    blurb: 'Stat tests, checklists, walkthroughs',
  },
]

export default function ProjectHomePage() {
  const projectId = useProjectId()
  const project = useProject()

  // All four stat queries are independent and parallelisable.
  const articlesQ = useQuery({
    queryKey: ['articles', projectId, { sort: 'created_desc' }],
    queryFn: () => articlesApi.list(projectId, { sort: 'created_desc' }),
  })
  const datasetsQ = useQuery({
    queryKey: ['datasets', projectId],
    queryFn: () => datasetsApi.list(projectId),
  })
  // Fan out one query per manuscript section to compute a total word count.
  const sectionQs = MANUSCRIPT_SECTIONS.map((s) =>
    useQuery({
      queryKey: ['manuscript-section', projectId, s],
      queryFn: () => manuscriptApi.getSection(projectId, s),
    }),
  )

  const manuscriptWords = sectionQs.reduce(
    (sum, q) => sum + (q.data?.word_count ?? 0),
    0,
  )

  const stats: ProjectStats = {
    articleCount: articlesQ.data?.length ?? 0,
    datasetCount: datasetsQ.data?.length ?? 0,
    manuscriptWords,
  }

  return (
    <motion.div
      variants={pageEnter}
      initial="initial"
      animate="animate"
      exit="exit"
      className="max-w-screen-2xl mx-auto px-8 py-10 space-y-8"
    >
      <header className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
            Project home
          </div>
          {project ? (
            <h1 className="mt-1 text-2xl font-semibold tracking-tight truncate">
              {project.title}
            </h1>
          ) : (
            <Skeleton className="mt-2 h-7 w-[320px]" />
          )}
          {project && (
            <div className="mt-2 flex items-center gap-2 flex-wrap">
              <Badge
                variant="secondary"
                className="text-[10px] uppercase tracking-wider font-medium"
              >
                {project.study_type}
              </Badge>
              <span className="text-[12px] text-muted-foreground">
                {project.citation_style.toUpperCase()} · {project.ai_provider}
              </span>
              {project.target_journal && (
                <span className="text-[12px] text-muted-foreground">
                  · {project.target_journal}
                </span>
              )}
            </div>
          )}
        </div>
      </header>

      <section>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 3xl:grid-cols-6 gap-3">
          {MODULES.map((m) => (
            <Link
              key={m.to}
              to={`/projects/${projectId}/${m.to}`}
              className="group rounded-lg border border-border bg-white p-4 hover:shadow-sm hover:border-accent/40 transition-all"
            >
              <div className="flex items-center gap-2 text-foreground">
                <m.icon className="h-4 w-4" />
                <span className="text-[14px] font-semibold tracking-tight">
                  {m.label}
                </span>
              </div>
              <div className="mt-3 text-[12px] text-muted-foreground line-clamp-2">
                {m.blurb}
              </div>
              <div className="mt-2 text-[12px] font-medium text-accent">
                {m.stat(stats)}
              </div>
            </Link>
          ))}
        </div>
      </section>

      <RecentActivity
        articlesPending={articlesQ.isLoading}
        articles={articlesQ.data?.slice(0, 5) ?? []}
        projectId={projectId}
      />

      {/* Phase S1 — per-project collaborator panel. */}
      <MembersPanel projectId={projectId} />
    </motion.div>
  )
}

function RecentActivity({
  articlesPending,
  articles,
  projectId,
}: {
  articlesPending: boolean
  articles: { id: string; title: string; created_at: string }[]
  projectId: string
}) {
  return (
    <section>
      <div className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
        Recent articles
      </div>
      <div className="mt-2 space-y-1.5">
        {articlesPending && (
          <>
            <Skeleton className="h-9 w-full rounded-md" />
            <Skeleton className="h-9 w-full rounded-md" />
            <Skeleton className="h-9 w-full rounded-md" />
          </>
        )}
        {!articlesPending && articles.length === 0 && (
          <div className="rounded-md border border-dashed border-border bg-white/40 px-3 py-3 text-[12px] text-muted-foreground">
            No articles yet. Open the Library to add some.
          </div>
        )}
        {articles.map((a) => (
          <Link
            key={a.id}
            to={`/projects/${projectId}/reader/${a.id}`}
            className="block rounded-md border border-border bg-white px-3 py-2 text-[13px] hover:border-accent/40 hover:shadow-sm transition-all truncate"
          >
            {a.title}
          </Link>
        ))}
      </div>
    </section>
  )
}
