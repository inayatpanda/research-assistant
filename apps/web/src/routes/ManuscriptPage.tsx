import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { useState } from 'react'

import { BibliographyPanel } from '@/components/bibliography/BibliographyPanel'
import { AbbreviationsPanel } from '@/components/manuscript/AbbreviationsPanel'
import { FinalManuscriptView } from '@/components/manuscript/FinalManuscriptView'
import { ManuscriptEditor } from '@/components/manuscript/ManuscriptEditor'
import { ReferenceIntegrityPanel } from '@/components/manuscript/ReferenceIntegrityPanel'
import {
  SectionTabs,
  type ManuscriptTab,
  useManuscriptTab,
} from '@/components/manuscript/SectionTabs'
import { WordCountBar } from '@/components/manuscript/WordCountBar'
import { ProjectSelectGate } from '@/components/library/ProjectSelectGate'
import { manuscriptApi, projectsApi, type ManuscriptSectionName } from '@/lib/api'
import { pageEnter } from '@/lib/motion'
import { useActiveProject } from '@/lib/projectContext'

const SECTIONS: ManuscriptSectionName[] = [
  'Abstract',
  'Introduction',
  'Methodology',
  'Results',
  'Discussion',
  'Conclusion',
]

// Map old Compile colour-tab params (?tab=intro|method|results|discussion) to manuscript sections,
// so 'Open in Manuscript' deep links from Phase 4 land correctly.
const COMPILE_TAB_TO_SECTION: Record<string, ManuscriptSectionName> = {
  intro: 'Introduction',
  method: 'Methodology',
  results: 'Results',
  discussion: 'Discussion',
}

export default function ManuscriptPage() {
  const projectId = useActiveProject((s) => s.projectId)
  const [tab, setTab] = useManuscriptTab()
  const [sectionWords, setSectionWords] = useState(0)

  // If the URL came from Compile's deep link with ?tab=intro, redirect once.
  if (typeof window !== 'undefined') {
    const params = new URLSearchParams(window.location.search)
    const compileTab = params.get('tab')
    if (compileTab && COMPILE_TAB_TO_SECTION[compileTab] && !params.get('section')) {
      const next = new URLSearchParams()
      next.set('section', COMPILE_TAB_TO_SECTION[compileTab])
      window.history.replaceState({}, '', `?${next.toString()}`)
    }
  }

  if (!projectId) return <ProjectSelectGate />

  return (
    <ManuscriptInner
      projectId={projectId}
      tab={tab}
      setTab={setTab}
      sectionWords={sectionWords}
      setSectionWords={setSectionWords}
    />
  )
}

function ManuscriptInner({
  projectId,
  tab,
  setTab,
  sectionWords,
  setSectionWords,
}: {
  projectId: string
  tab: ManuscriptTab
  setTab: (t: ManuscriptTab) => void
  sectionWords: number
  setSectionWords: (n: number) => void
}) {
  const { data: project } = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => projectsApi.get(projectId),
  })

  // Word counts per section for the tab badges
  const sectionQueries = SECTIONS.map((s) =>
    useQuery({
      queryKey: ['manuscript-section', projectId, s],
      queryFn: () => manuscriptApi.getSection(projectId, s),
    }),
  )

  const wordCounts: Partial<Record<ManuscriptTab, number>> = {}
  let total = 0
  SECTIONS.forEach((s, i) => {
    const wc = sectionQueries[i].data?.word_count ?? 0
    wordCounts[s] = wc
    total += wc
  })

  const isFinal = tab === 'final'
  const activeSavedAt =
    !isFinal && SECTIONS.includes(tab as ManuscriptSectionName)
      ? sectionQueries[SECTIONS.indexOf(tab as ManuscriptSectionName)].data?.updated_at ?? null
      : null

  return (
    <motion.div
      variants={pageEnter}
      initial="initial"
      animate="animate"
      exit="exit"
      className="flex h-[calc(100vh-56px)]"
    >
      <div className="flex-1 min-w-0 flex flex-col">
        <header className="px-6 py-3 border-b border-border">
          <div className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
            Manuscript · {project?.title ?? 'Loading…'}
          </div>
          <h1 className="mt-0.5 text-[18px] font-semibold tracking-tight">
            {isFinal ? 'Final Manuscript' : tab}
          </h1>
        </header>

        <SectionTabs active={tab} onChange={setTab} wordCounts={wordCounts} />

        {isFinal ? (
          <FinalManuscriptView projectId={projectId} />
        ) : (
          <ManuscriptEditor
            key={`${projectId}-${tab}`}
            projectId={projectId}
            section={tab as ManuscriptSectionName}
            onWordsChange={setSectionWords}
          />
        )}

        {!isFinal && (
          <WordCountBar
            sectionWords={sectionWords || wordCounts[tab] || 0}
            totalWords={total}
            saving={false}
            savedAt={activeSavedAt}
          />
        )}
      </div>

      <aside className="hidden xl:flex shrink-0 w-[340px] flex-col border-l border-border bg-zinc-50 p-4 space-y-3 overflow-y-auto">
        <BibliographyPanel projectId={projectId} />
        <ReferenceIntegrityPanel projectId={projectId} />
        <AbbreviationsPanel projectId={projectId} />
      </aside>
    </motion.div>
  )
}
