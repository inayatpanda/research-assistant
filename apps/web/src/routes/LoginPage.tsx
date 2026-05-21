import { useLocation } from 'react-router-dom'

import { LoginForm } from '@/components/auth/LoginForm'

type LocationState = { from?: string } | null

export default function LoginPage() {
  const location = useLocation()
  const state = location.state as LocationState
  const redirectTo = state?.from ?? '/'
  return (
    <div className="flex min-h-[70vh] items-center justify-center px-4">
      <LoginForm redirectTo={redirectTo} />
    </div>
  )
}
