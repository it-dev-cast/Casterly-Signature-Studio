const KEY = 'sigstudio.token'

// "Remember me" keeps the token in localStorage; otherwise it lives for the tab session.
function safe<T>(fn: () => T, fallback: T): T {
  try {
    return fn()
  } catch {
    return fallback
  }
}

export const tokenStorage = {
  get(): string | null {
    return safe(() => localStorage.getItem(KEY) ?? sessionStorage.getItem(KEY), null)
  },
  set(token: string, remember: boolean) {
    safe(() => {
      this.clear()
      ;(remember ? localStorage : sessionStorage).setItem(KEY, token)
    }, undefined)
  },
  clear() {
    safe(() => {
      localStorage.removeItem(KEY)
      sessionStorage.removeItem(KEY)
    }, undefined)
  },
}
