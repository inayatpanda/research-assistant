import { ClipboardList } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

import { Button } from '@/components/ui/button'

export function EmptyReviewState({ studyType }: { studyType?: string | null }) {
  const navigate = useNavigate()
  const mismatched = !!studyType && studyType !== 'Systematic Review'

  return (
    <div className="max-w-2xl mx-auto px-8 py-16 text-center">
      <ClipboardList className="h-8 w-8 mx-auto text-muted-foreground" />
      <h2 className="mt-4 text-[20px] font-semibold tracking-tight">
        {mismatched ? 'This project is not a Systematic Review' : 'Set up your review'}
      </h2>
      <p className="mt-2 text-[14px] text-muted-foreground">
        {mismatched
          ? `Current study type is "${studyType}". Switch the project to Systematic Review in Settings to use this workspace.`
          : 'Capture PICO, eligibility, search records, screening decisions, risk of bias and data extraction in one place. PRISMA flow is generated for you.'}
      </p>
      <Button
        onClick={() => navigate('/settings')}
        variant="outline"
        className="mt-6"
      >
        Open settings
      </Button>
    </div>
  )
}
