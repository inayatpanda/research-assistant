import { useState } from 'react'

import { AffiliationsEditor } from './AffiliationsEditor'
import { AuthorsEditor } from './AuthorsEditor'
import { ContributionsMatrix } from './ContributionsMatrix'
import { EthicsFundingForm } from './EthicsFundingForm'
import { StructuredAbstract } from './StructuredAbstract'

type Section = 'authors' | 'affiliations' | 'contributions' | 'ethics' | 'abstract'

const SECTIONS: Array<{ id: Section; label: string }> = [
  { id: 'authors', label: 'Authors' },
  { id: 'affiliations', label: 'Affiliations' },
  { id: 'contributions', label: 'Contributions' },
  { id: 'ethics', label: 'Ethics & funding' },
  { id: 'abstract', label: 'Structured abstract' },
]

export function FrontMatterPanel({ projectId }: { projectId: string }) {
  const [section, setSection] = useState<Section>('authors')

  return (
    <div className="flex flex-col h-full">
      <div className="flex gap-1 border-b border-border px-2 overflow-x-auto">
        {SECTIONS.map((s) => {
          const active = s.id === section
          return (
            <button
              key={s.id}
              onClick={() => setSection(s.id)}
              data-testid={`fm-section-${s.id}`}
              className={`px-3 py-2 text-sm whitespace-nowrap border-b-2 ${
                active
                  ? 'border-accent text-foreground'
                  : 'border-transparent text-muted-foreground hover:text-foreground'
              }`}
            >
              {s.label}
            </button>
          )
        })}
      </div>
      <div className="flex-1 overflow-y-auto p-4">
        {section === 'authors' && <AuthorsEditor projectId={projectId} />}
        {section === 'affiliations' && (
          <AffiliationsEditor projectId={projectId} />
        )}
        {section === 'contributions' && (
          <ContributionsMatrix projectId={projectId} />
        )}
        {section === 'ethics' && <EthicsFundingForm projectId={projectId} />}
        {section === 'abstract' && <StructuredAbstract projectId={projectId} />}
      </div>
    </div>
  )
}
