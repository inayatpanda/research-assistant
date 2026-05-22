import '@testing-library/jest-dom/vitest'

// Phase L1c — jsdom v29 + Node 26 stopped exposing window.localStorage
// out of the box. We polyfill an in-memory Storage so the licence-flow
// pages (Signup/Login/Account) can persist tokens during tests.
if (typeof window !== 'undefined' && !window.localStorage) {
  const store = new Map<string, string>()
  const storage: Storage = {
    get length() {
      return store.size
    },
    clear() {
      store.clear()
    },
    getItem(key: string) {
      return store.has(key) ? (store.get(key) as string) : null
    },
    key(i: number) {
      return Array.from(store.keys())[i] ?? null
    },
    removeItem(key: string) {
      store.delete(key)
    },
    setItem(key: string, value: string) {
      store.set(key, String(value))
    },
  }
  Object.defineProperty(window, 'localStorage', {
    configurable: true,
    value: storage,
  })
}
