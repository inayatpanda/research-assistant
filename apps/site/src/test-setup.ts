import '@testing-library/jest-dom/vitest'

// Phase v0.3 — framer-motion's useInView requires IntersectionObserver,
// which jsdom doesn't ship. We polyfill a no-op observer that never
// fires "intersect" — RevealOnScroll already handles the "never in
// view" case by rendering children flat, so tests still see content.
if (typeof window !== 'undefined' && !('IntersectionObserver' in window)) {
  class MockIntersectionObserver {
    readonly root = null
    readonly rootMargin = ''
    readonly thresholds: ReadonlyArray<number> = []
    observe() {}
    unobserve() {}
    disconnect() {}
    takeRecords(): IntersectionObserverEntry[] {
      return []
    }
  }
  ;(window as unknown as { IntersectionObserver: typeof IntersectionObserver }).IntersectionObserver =
    MockIntersectionObserver as unknown as typeof IntersectionObserver
  ;(globalThis as unknown as { IntersectionObserver: typeof IntersectionObserver }).IntersectionObserver =
    MockIntersectionObserver as unknown as typeof IntersectionObserver
}

// Phase v0.3 — jsdom doesn't implement matchMedia. framer-motion's
// useReducedMotion calls it; without this shim RevealOnScroll throws
// during render.
if (typeof window !== 'undefined' && typeof window.matchMedia !== 'function') {
  Object.defineProperty(window, 'matchMedia', {
    configurable: true,
    writable: true,
    value: (query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    }),
  })
}

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
