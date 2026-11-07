import { useEffect, useRef, useState, useSyncExternalStore } from 'react'
import { Navigate, Outlet, useLocation } from 'react-router'

import { fetchMe } from '../../api/authApi'
import { API_BASE, silentRefreshAccessToken } from '../../api/rawClient'
import { AUTH_NEXT_PATH_KEY, SKIP_LOGOUT_BEACON_ONCE_KEY } from '../../constants/auth'
import { useAuthStore } from '../../store/authStore'
import { sanitizeUserAvatarUrl } from '../../utils/avatar/sanitizeUserAvatarUrl'
import { shouldSaveAuthNextPath } from '../../utils/auth/authNextPath'

/** За сколько до истечения access token пробуем проактивный refresh (мс). */
const REFRESH_BEFORE_EXPIRY_MS = 90_000

/** При возврате на вкладку обновить токен, если до истечения осталось не больше этого интервала. */
const REFRESH_ON_VISIBLE_IF_WITHIN_MS = 120_000

function useAccessExpired(expiresAt: number | null): boolean {
  const stateRef = useRef({ expired: false, deadline: null as number | null })

  return useSyncExternalStore(
    (onStoreChange) => {
      stateRef.current.deadline = expiresAt

      const sync = () => {
        const deadline = stateRef.current.deadline
        const next = deadline !== null && Date.now() >= deadline
        if (next !== stateRef.current.expired) {
          stateRef.current.expired = next
          onStoreChange()
        }
      }

      sync()

      if (expiresAt === null || Date.now() >= expiresAt) {
        return () => undefined
      }

      const ms = expiresAt - Date.now()
      const id = window.setTimeout(sync, ms)
      return () => window.clearTimeout(id)
    },
    () => stateRef.current.expired,
    () => false,
  )
}

export function RequireAuth() {
  const accessToken = useAuthStore((s) => s.accessToken)
  const expiresAt = useAuthStore((s) => s.expiresAt)
  const patchUser = useAuthStore((s) => s.patchUser)
  const location = useLocation()

  const [initialRefreshDone, setInitialRefreshDone] = useState(
    // Пробуем тихий refresh, если accessToken нет, но expiresAt задан (cookie с refresh-токеном может быть).
    () => !!useAuthStore.getState().accessToken || !useAuthStore.getState().expiresAt,
  )

  useEffect(() => {
    if (initialRefreshDone) return
    void silentRefreshAccessToken().finally(() => setInitialRefreshDone(true))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const isExpired = useAccessExpired(expiresAt)

  useEffect(() => {
    if (!accessToken) return
    void fetchMe()
      .then((fresh) =>
        patchUser({
          ...fresh,
          avatar_url: sanitizeUserAvatarUrl(fresh.avatar_url) ?? null,
        }),
      )
      // best-effort фоновое обновление профиля: при сетевой ошибке не тревожим пользователя
      // тостом — профиль остаётся из persist, а следующий успешный refresh его обновит.
      .catch(() => undefined)
  }, [accessToken, patchUser])

  useEffect(() => {
    if (!isExpired) return
    void silentRefreshAccessToken()
  }, [isExpired])

  useEffect(() => {
    if (!accessToken || !expiresAt) return
    const delay = expiresAt - Date.now() - REFRESH_BEFORE_EXPIRY_MS
    if (delay <= 0) {
      void silentRefreshAccessToken()
      return
    }
    const id = window.setTimeout(() => void silentRefreshAccessToken(), delay)
    return () => window.clearTimeout(id)
  }, [accessToken, expiresAt])

  useEffect(() => {
    if (!accessToken) return
    const onVis = () => {
      if (document.visibilityState !== 'visible') return
      const exp = useAuthStore.getState().expiresAt
      if (exp != null && exp - Date.now() <= REFRESH_ON_VISIBLE_IF_WITHIN_MS) {
        void silentRefreshAccessToken()
      }
    }
    document.addEventListener('visibilitychange', onVis)
    return () => document.removeEventListener('visibilitychange', onVis)
  }, [accessToken])

  useEffect(() => {
    const path = location.pathname + location.search
    if (!shouldSaveAuthNextPath(path)) return
    // best-effort: в приватном режиме / при переполнении quota запись молча пропускается —
    // это не критично, post-login redirect просто откатится к '/'.
    try {
      sessionStorage.setItem(AUTH_NEXT_PATH_KEY, path)
    } catch {
      /* ignore */
    }
  }, [location.pathname, location.search])

  // Интервальный fallback: проверяет каждые 60 секунд, не нужен ли refresh.
  // Страхует от браузерного throttling setTimeout в фоновых вкладках.
  useEffect(() => {
    if (!accessToken) return
    const id = window.setInterval(() => {
      const { expiresAt: exp } = useAuthStore.getState()
      if (exp != null && exp - Date.now() <= REFRESH_BEFORE_EXPIRY_MS) {
        void silentRefreshAccessToken()
      }
    }, 60_000)
    return () => window.clearInterval(id)
  }, [accessToken])

  // Отправляем logout-beacon при закрытии вкладки: инвалидирует Redis-кэш access token.
  // sendBeacon не поддерживает заголовки Authorization, поэтому токен передаётся в теле.
  useEffect(() => {
    const handleUnload = () => {
      if (sessionStorage.getItem(SKIP_LOGOUT_BEACON_ONCE_KEY)) {
        sessionStorage.removeItem(SKIP_LOGOUT_BEACON_ONCE_KEY)
        return
      }
      const token = useAuthStore.getState().accessToken
      if (!token) return
      const body = JSON.stringify({ access_token: token })
      navigator.sendBeacon(`${API_BASE}/auth/logout-beacon`, new Blob([body], { type: 'application/json' }))
    }
    window.addEventListener('beforeunload', handleUnload)
    return () => window.removeEventListener('beforeunload', handleUnload)
  }, [])

  if (!initialRefreshDone) {
    return <p className="text-muted">Загрузка…</p>
  }

  if (!accessToken) {
    return <Navigate to="/login" replace />
  }

  return <Outlet />
}
