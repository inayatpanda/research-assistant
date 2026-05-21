import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useLogin } from '@/hooks/useAuth'

export type LoginFormProps = {
  redirectTo?: string
}

export function LoginForm({ redirectTo = '/' }: LoginFormProps) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const login = useLogin()
  const navigate = useNavigate()

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    try {
      await login.mutateAsync({ email, password })
      navigate(redirectTo, { replace: true })
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Login failed'
      setError(msg)
    }
  }

  return (
    <form
      onSubmit={onSubmit}
      data-testid="login-form"
      className="flex w-full max-w-sm flex-col gap-4 rounded-md border bg-card p-6 shadow-sm"
    >
      <h1 className="text-xl font-semibold">Sign in</h1>
      <div className="grid gap-2">
        <Label htmlFor="login-email">Email</Label>
        <Input
          id="login-email"
          type="email"
          autoComplete="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
      </div>
      <div className="grid gap-2">
        <Label htmlFor="login-password">Password</Label>
        <Input
          id="login-password"
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
      </div>
      {error ? (
        <p
          role="alert"
          className="text-sm text-destructive"
          data-testid="login-error"
        >
          {error}
        </p>
      ) : null}
      <Button type="submit" disabled={login.isPending}>
        {login.isPending ? 'Signing in…' : 'Sign in'}
      </Button>
      <p className="text-sm text-muted-foreground">
        No account?{' '}
        <a className="underline" href="/signup">
          Create one
        </a>
      </p>
    </form>
  )
}

export default LoginForm
