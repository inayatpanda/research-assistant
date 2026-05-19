/**
 * Phase 17 (MP17) — Analysis-plan pre-registration lock button.
 *
 * Confirmation dialog + integrity-hash display once locked.
 */
import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'

import { analysisPlanLockApi } from '../../lib/api'

interface Props {
  projectId: string
  planId: string
  isLocked?: boolean
  integrityHash?: string | null
  lockedAt?: string | null
  onLocked?: () => void
}

export function AnalysisPlanLockButton({
  projectId,
  planId,
  isLocked = false,
  integrityHash,
  lockedAt,
  onLocked,
}: Props) {
  const [confirming, setConfirming] = useState(false)
  const lockMutation = useMutation({
    mutationFn: () => analysisPlanLockApi.lock(projectId, planId),
    onSuccess: () => {
      setConfirming(false)
      onLocked?.()
    },
  })

  if (isLocked) {
    return (
      <div data-testid="lock-status">
        <strong>Locked</strong>
        {lockedAt ? <p>Locked at: {lockedAt}</p> : null}
        {integrityHash ? (
          <p>
            Integrity hash: <code>{integrityHash}</code>
          </p>
        ) : null}
      </div>
    )
  }

  if (!confirming) {
    return (
      <button onClick={() => setConfirming(true)} data-testid="lock-trigger">
        Lock plan (pre-register)
      </button>
    )
  }

  return (
    <div data-testid="lock-confirm">
      <p>
        Locking computes a SHA-256 integrity hash of the plan steps and freezes
        the plan. Subsequent edits will require an explicit force-unlock.
      </p>
      <button onClick={() => lockMutation.mutate()} disabled={lockMutation.isPending}>
        Confirm lock
      </button>
      <button onClick={() => setConfirming(false)}>Cancel</button>
      {lockMutation.error ? (
        <p role="alert">Failed to lock plan.</p>
      ) : null}
    </div>
  )
}

export default AnalysisPlanLockButton
