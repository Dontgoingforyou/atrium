/**
 * Тема: `data-theme` на `html` + localStorage (zustand persist).
 */
import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export type ThemeId = 'light' | 'dark'

export const THEME_PERSIST_KEY = 'cosmolet-theme'

const DEFAULT_THEME: ThemeId = 'light'

function readPersistedTheme(): ThemeId {
  if (typeof localStorage === 'undefined') return DEFAULT_THEME
  try {
    const raw = localStorage.getItem(THEME_PERSIST_KEY)
    if (!raw) return DEFAULT_THEME
    const parsed = JSON.parse(raw) as { state?: { theme?: unknown } }
    const t = parsed.state?.theme
    if (t === 'light' || t === 'dark') return t
  } catch {
    /* ignore */
  }
  return DEFAULT_THEME
}

function applyThemeToDocument(theme: ThemeId): void {
  document.documentElement.setAttribute('data-theme', theme)
}

function prefersReducedMotion(): boolean {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

let activeThemeViewTransition: ViewTransition | null = null

function applyThemeUpdate(theme: ThemeId, set: (partial: { theme: ThemeId }) => void): void {
  set({ theme })
  applyThemeToDocument(theme)
}

interface ThemeState {
  theme: ThemeId
  setTheme: (theme: ThemeId) => void
}

export const useThemeStore = create<ThemeState>()(
  persist(
    (set) => ({
      theme: readPersistedTheme(),
      setTheme: (theme) => {
        const update = () => applyThemeUpdate(theme, set)

        if (prefersReducedMotion()) {
          update()
          return
        }

        const doc = document as Document & { startViewTransition?: (cb: () => void) => ViewTransition }
        if (typeof doc.startViewTransition !== 'function') {
          update()
          return
        }

        if (activeThemeViewTransition) {
          try {
            activeThemeViewTransition.skipTransition()
          } catch {
            /* переход уже завершён */
          }
        }

        const vt = doc.startViewTransition(update)
        activeThemeViewTransition = vt
        void vt.finished.finally(() => {
          if (activeThemeViewTransition === vt) {
            activeThemeViewTransition = null
          }
        })
      },
    }),
    {
      name: THEME_PERSIST_KEY,
      partialize: (s) => ({ theme: s.theme }),
      onRehydrateStorage: () => (state) => {
        if (state?.theme) {
          applyThemeToDocument(state.theme)
        }
      },
    },
  ),
)

export const THEME_OPTIONS: { id: ThemeId; label: string; icon: string }[] = [
  { id: 'light', label: 'Светлая', icon: '☀️' },
  { id: 'dark', label: 'Тёмная', icon: '🌙' },
]
