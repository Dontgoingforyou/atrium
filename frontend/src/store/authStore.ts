import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { apiFetch } from '../api/rawClient'
import { AUTH_PERSIST_KEY } from '../constants/auth'
import { clearDocsBearerToken } from '../constants/docsAuth'
import type { AuthUser } from '../types/auth'

interface AuthState {
  accessToken: string | null
  expiresAt: number | null
  /** OAuth client_id бэкенда для этого входа (нужен для /auth/refresh при нескольких клиентах) */
  oauthClientId: string | null
  user: AuthUser | null
  setSession: (payload: {
    access_token: string
    expires_in: number
    oauth_client_id: string
    user: AuthUser
  }) => void
  clearSession: () => void
  /** Полный выход: инвалидирует токен на бэкенде + очищает локальную сессию. */
  logout: () => Promise<void>
  /** Частичное обновление профиля (аватар и т.д.) без перевыдачи токена. */
  patchUser: (partial: Partial<AuthUser>) => void
}

// Refresh-токен хранится в httpOnly cookie на бэкенде (BFF-паттерн), недоступен для JS.
// В localStorage сохраняются только oauthClientId, expiresAt и user для UX (silent refresh).
// accessToken намеренно не в persist — сбрасывается при перезагрузке страницы.
export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      accessToken: null,
      expiresAt: null,
      oauthClientId: null,
      user: null,
      setSession: (payload) =>
        set({
          accessToken: payload.access_token,
          expiresAt: Date.now() + payload.expires_in * 1000,
          oauthClientId: payload.oauth_client_id,
          user: payload.user,
        }),
      clearSession: () => {
        clearDocsBearerToken()
        set({
          accessToken: null,
          expiresAt: null,
          oauthClientId: null,
          user: null,
        })
      },
      logout: async () => {
        const token = get().accessToken
        if (token) {
          try {
            await apiFetch('/auth/logout', {
              method: 'POST',
              headers: { Authorization: `Bearer ${token}` },
              credentials: 'include',
              keepalive: true,
            })
          } catch (err) {
            // best-effort: даже при ошибке сети — очищаем сессию.
            // Тост не нужен (пользователь уходит на /login), но в dev — аудит-след.
            if (import.meta.env.DEV) {
              console.warn('logout: не удалось вызвать /auth/logout', err)
            }
          }
        }
        get().clearSession()
      },
      patchUser: (partial) =>
        set((state) =>
          state.user ? { user: { ...state.user, ...partial } } : {},
        ),
    }),
    {
      name: AUTH_PERSIST_KEY,
      partialize: (state) => ({
        expiresAt: state.expiresAt,
        oauthClientId: state.oauthClientId,
        user: state.user,
      }),
    },
  ),
)

// Синхронизация между вкладками: при обновлении persist в другой вкладке — ре-гидрация,
// чтобы не держать устаревший refresh после ротации.
if (typeof window !== 'undefined') {
  window.addEventListener('storage', (e) => {
    if (e.key === AUTH_PERSIST_KEY) {
      void useAuthStore.persist.rehydrate()
    }
  })
}
