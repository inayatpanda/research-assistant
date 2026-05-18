/**
 * Phase 12 — Submission page.
 *
 * Hosts the three submission helpers: cover letter editor, reviewer
 * response editor, and a button that opens the submission-package
 * download dialog. Mounted at /projects/:projectId/submission via the
 * ProjectLayoutGuard so projectId is always present.
 */
import { CoverLetterEditor } from '@/components/submission/CoverLetterEditor'
import { ReviewerResponseEditor } from '@/components/submission/ReviewerResponseEditor'
import { SubmissionPackageDialog } from '@/components/submission/SubmissionPackageDialog'
import { useProjectId } from '@/lib/projectContext'

export default function SubmissionPage() {
  const projectId = useProjectId()

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
