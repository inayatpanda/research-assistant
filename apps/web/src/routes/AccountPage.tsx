import { AccountPanel } from '@/components/auth/AccountPanel'

export default function AccountPage() {
  return (
    <div className="container mx-auto max-w-3xl px-4 py-8">
      <h1 className="mb-6 text-2xl font-semibold">Account</h1>
      <AccountPanel />
    </div>
  )
}
