import { useLocation } from 'react-router-dom'

import { SignupForm } from '@/components/auth/SignupForm'

type LocationState = { from?: string } | null

export default function SignupPage() {
  const location = useLocation()
  const state = location.state as LocationState
  const redirectTo = state?.from ?? '/'
  return (
    <div className="flex min-h-[70vh] items-center justify-center px-4">
      <SignupForm redirectTo={redirectTo} />
    </div>
  )
}
