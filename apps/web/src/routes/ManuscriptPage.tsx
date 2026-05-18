import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { useCallback, useEffect, useRef, useState } from 'react'
import type { Editor } from '@tiptap/react'

import { BibliographyPanel } from '@/components/bibliography/BibliographyPanel'
import { FiguresPanel } from '@/components/figures/FiguresPanel'
import { FrontMatterPanel } from '@/components/frontmatter/FrontMatterPanel'
import { AbbreviationsPanel } from '@/components/manuscript/AbbreviationsPanel'
import { FinalManuscriptView } from '@/components/manuscript/FinalManuscriptView'
import { JournalChip } from '@/components/manuscript/JournalChip'
import { ManuscriptEditor } from '@/components/manuscript/ManuscriptEditor'
import {
  ManuscriptSearchPanel,
  type SearchHit,
  type SectionHtml,
} from '@/components/manuscript/ManuscriptSearchPanel'
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
  const [editor, setEditor] = useState<Editor | null>(null)
  const [searchOpen, setSearchOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const editorPaneRef = useRef<HTMLDivElement | null>(null)

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
  const isFrontMatter = tab === 'frontmatter'
  const activeSavedAt =
    !isFinal && SECTIONS.includes(tab as ManuscriptSectionName)
      ? sectionQueries[SECTIONS.indexOf(tab as ManuscriptSectionName)].data?.updated_at ?? null
      : null

  // Aggregate section HTML for the cross-section search panel.
  const sectionSnapshots: SectionHtml[] = SECTIONS.map((s, i) => ({
    section: s,
    html: sectionQueries[i].data?.content ?? '',
  }))

  // Cmd-F / Ctrl-F intercept: open the cross-section search panel ONLY when
  // the manuscript editor or the search panel itself has focus. Outside that
  // zone the browser's native Find stays untouched.
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const isFind =
        (e.metaKey || e.ctrlKey) && !e.shiftKey && !e.altKey && e.key.toLowerCase() === 'f'
      if (!isFind) return
      const pane = editorPaneRef.current
      if (!pane) return
      const focused = document.activeElement as HTMLElement | null
      // Only intercept when focus is inside the manuscript editor pane OR
      // the search panel (so Cmd-F while the panel is open re-focuses it).
      if (focused && pane.contains(focused)) {
        e.preventDefault()
        setSearchOpen(true)
      }
    }
    document.addEventListener('keydown', onKey, true)
    return () => document.removeEventListener('keydown', onKey, true)
  }, [])

  const handleJump = useCallback(
    (hit: SearchHit) => {
      // Switch to the target section tab if needed; this remounts the editor
      // (its key includes `tab`), so the selection placement must happen
      // AFTER the next render.
      const needsSwitch = hit.section !== tab
      if (needsSwitch) setTab(hit.section)
      const place = () => {
        if (!editor) return
        const doc = editor.state.doc
        const needle = hit.query.toLowerCase()
        let seen = 0
        let targetPos: number | null = null
        doc.descendants((node, pos) => {
          if (targetPos != null) return false
          if (!node.isText) return true
          const text = (node.text ?? '').toLowerCase()
          let from = 0
          while (true) {
            const at = text.indexOf(needle, from)
            if (at < 0) break
            if (seen === hit.matchIndex) {
              targetPos = pos + at
              return false
            }
            seen += 1
            from = at + needle.length
          }
          return true
        })
        if (targetPos != null) {
          editor.commands.focus()
          editor.commands.setTextSelection({
            from: targetPos,
            to: targetPos + hit.length,
          })
          editor.commands.scrollIntoView()
        }
      }
      if (needsSwitch) setTimeout(place, 50)
      else place()
    },
    [editor, tab, setTab],
  )

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
          <div className="flex items-center justify-between">
            <div className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
              Manuscript · {project?.title ?? 'Loading…'}
            </div>
            <JournalChip templateKey={project?.template_journal ?? null} />
          </div>
          <h1 className="mt-0.5 text-[18px] font-semibold tracking-tight">
            {isFinal
              ? 'Final Manuscript'
              : isFrontMatter
              ? 'Front matter (ICMJE)'
              : tab}
          </h1>
        </header>

        <SectionTabs active={tab} onChange={setTab} wordCounts={wordCounts} />

        <div ref={editorPaneRef} className="relative flex-1 min-h-0 flex flex-col">
          {searchOpen && !isFinal && (
            <ManuscriptSearchPanel
              sections={sectionSnapshots}
              onJump={(hit) => {
                setSearchQuery(hit.query)
                handleJump(hit)
              }}
              onClose={() => setSearchOpen(false)}
            />
          )}
          {isFinal ? (
            <FinalManuscriptView projectId={projectId} />
          ) : isFrontMatter ? (
            <FrontMatterPanel projectId={projectId} />
          ) : (
            <ManuscriptEditor
              key={`${projectId}-${tab}`}
              projectId={projectId}
              section={tab as ManuscriptSectionName}
              onWordsChange={setSectionWords}
              onEditorReady={setEditor}
            />
          )}
        </div>

        {!isFinal && !isFrontMatter && (
          <WordCountBar
            sectionWords={sectionWords || wordCounts[tab] || 0}
            totalWords={total}
            saving={false}
            savedAt={activeSavedAt}
            templateKey={project?.template_journal ?? null}
            activeSectionName={tab as string}
          />
        )}
      </div>

      <aside className="hidden xl:flex shrink-0 w-[340px] flex-col border-l border-border bg-zinc-50 p-4 space-y-3 overflow-y-auto">
        <FiguresPanel projectId={projectId} editor={editor} />
        <BibliographyPanel projectId={projectId} />
        <ReferenceIntegrityPanel projectId={projectId} />
        <AbbreviationsPanel projectId={projectId} />
      </aside>
    </motion.div>
  )
}
