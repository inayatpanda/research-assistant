import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useSignup } from '@/hooks/useAuth'

export type SignupFormProps = {
  redirectTo?: string
}

function validatePassword(pw: string): string | null {
  if (pw.length < 10) return 'Password must be at least 10 characters.'
  if (!/\d/.test(pw)) return 'Password must contain at least one digit.'
  return null
}

export function SignupForm({ redirectTo = '/' }: SignupFormProps) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [tosAcknowledged, setTosAcknowledged] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const signup = useSignup()
  const navigate = useNavigate()

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    if (!tosAcknowledged) {
      setError('Please acknowledge the local-storage notice.')
      return
    }
    const v = validatePassword(password)
    if (v) {
      setError(v)
      return
    }
    try {
      await signup.mutateAsync({ email, password, display_name: displayName })
      navigate(redirectTo, { replace: true })
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Signup failed'
      setError(msg)
    }
  }

  return (
    <form
      onSubmit={onSubmit}
      data-testid="signup-form"
      className="flex w-full max-w-sm flex-col gap-4 rounded-md border bg-card p-6 shadow-sm"
    >
      <h1 className="text-xl font-semibold">Create an account</h1>
      <div className="grid gap-2">
        <Label htmlFor="signup-name">Display name</Label>
        <Input
          id="signup-name"
          type="text"
          autoComplete="name"
          value={displayName}
          onChange={(e) => setDisplayName(e.target.value)}
          required
        />
      </div>
      <div className="grid gap-2">
        <Label htmlFor="signup-email">Email</Label>
        <Input
          id="signup-email"
          type="email"
          autoComplete="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
      </div>
      <div className="grid gap-2">
        <Label htmlFor="signup-password">Password</Label>
        <Input
          id="signup-password"
          type="password"
          autoComplete="new-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          aria-describedby="signup-pw-help"
        />
        <p id="signup-pw-help" className="text-xs text-muted-foreground">
          At least 10 characters and one digit.
        </p>
      </div>
      <label className="flex items-start gap-2 text-sm text-muted-foreground">
        <input
          type="checkbox"
          checked={tosAcknowledged}
          onChange={(e) => setTosAcknowledged(e.target.checked)}
          className="mt-1"
          data-testid="signup-tos"
        />
        <span>
          I understand that my research data stays on this device unless I
          explicitly share a project with someone over the tailnet.
        </span>
      </label>
      {error ? (
        <p
          role="alert"
          className="text-sm text-destructive"
          data-testid="signup-error"
        >
          {error}
        </p>
      ) : null}
      <Button type="submit" disabled={signup.isPending}>
        {signup.isPending ? 'Creating account…' : 'Create account'}
      </Button>
      <p className="text-sm text-muted-foreground">
        Already have an account?{' '}
        <a className="underline" href="/login">
          Sign in
        </a>
      </p>
    </form>
  )
}

export default SignupForm
