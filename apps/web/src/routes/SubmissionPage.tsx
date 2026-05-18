/**
 * Phase 12 — Submission page.
 *
 * Hosts the three submission helpers: cover letter editor, reviewer
 * response editor, and a button that opens the submission-package
 * download dialog. Mounted at /submission so it can be linked from the
 * dashboard or the manuscript header dropdown.
 */
import { CoverLetterEditor } from '@/components/submission/CoverLetterEditor'
import { ReviewerResponseEditor } from '@/components/submission/ReviewerResponseEditor'
import { SubmissionPackageDialog } from '@/components/submission/SubmissionPackageDialog'
import { useActiveProject } from '@/lib/projectContext'

export default function SubmissionPage() {
  const projectId = useActiveProject((s) => s.projectId)

  if (!projectId) {
    return (
      <div className="p-6 text-sm text-muted-foreground">
        Select a project from the dashboard to access submission tools.
      </div>
    )
  }

  return (
    <div className="space-y-6 p-6 max-w-5xl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Submission</h1>
          <p className="text-sm text-muted-foreground">
            Cover letter, reviewer responses, and the one-click submission
            package zip.
          </p>
        </div>
        <SubmissionPackageDialog projectId={projectId} />
      </div>
      <CoverLetterEditor projectId={projectId} />
      <ReviewerResponseEditor projectId={projectId} />
    </div>
  )
}
