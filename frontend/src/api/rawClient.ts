import { useAuthStore } from '../store/authStore'

/** Базовый префикс API (через Vite proxy совпадает с FastAPI `/api/v1`). */
export const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined)?.replace(/\/$/, '') || '/api/v1'

export async function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const p = path.startsWith('/') ? path : `/${path}`
  return fetch(`${API_BASE}${p}`, init)
}

// ─── Тихий refresh ──────────────────────────────────────────────────────────

let _refreshPromise: Promise<string | null> | null = null

/**
 * Обновление access token через httpOnly cookie refresh-токен.
 * Refresh-токен хранится в cookie 'rt' (httpOnly, недоступен JS) — браузер отправляет его автоматически.
 * Дедупликация параллельных вызовов.
 */
export async function silentRefreshAccessToken(): Promise<string | null> {
  if (_refreshPromise) return _refreshPromise

  _refreshPromise = (async () => {
    try {
      const { oauthClientId, expiresAt, clearSession } = useAuthStore.getState()

      // Если expiresAt не задан — сессия не инициализирована, нет смысла рефрешить
      if (!expiresAt) {
        clearSession()
        return null
      }

      const body: Record<string, string> = {}
      if (oauthClientId) {
        body.client_id = oauthClientId
      }

      const res = await apiFetch('/auth/refresh', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',  // отправить httpOnly cookie 'rt'
        body: JSON.stringify(body),
      })

      if (!res.ok) {
        clearSession()
        return null
      }

      const data = (await res.json()) as {
        access_token: string
        refresh_token?: string | null
        expires_in: number
        oauth_client_id: string
      }
      const prev = useAuthStore.getState()
      if (!prev.user) {
        prev.clearSession()
        return null
      }
      useAuthStore.getState().setSession({
        access_token: data.access_token,
        expires_in: data.expires_in,
        oauth_client_id: data.oauth_client_id ?? prev.oauthClientId,
        user: prev.user,
      })
      return data.access_token
    } catch {
      // Сетевой сбой и т.п. — сессию не сбрасываем; повторит таймер, вкладка или следующий запрос
      return null
    } finally {
      _refreshPromise = null
    }
  })()

  return _refreshPromise
}

// ─── Аутентифицированный fetch ───────────────────────────────────────────────

/**
 * Обёртка над `apiFetch` для защищённых эндпоинтов:
 * - Автоматически добавляет `Authorization: Bearer` из стора.
 * - При получении 401 пробует тихо обновить токен через refresh и повторяет запрос.
 * - При неудачном refresh очищает сессию (пользователь будет перенаправлен на /login через RequireAuth).
 */
export async function authenticatedFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const token = useAuthStore.getState().accessToken

  const headers = new Headers(init.headers)
  if (token) headers.set('Authorization', `Bearer ${token}`)

  const firstResponse = await apiFetch(path, { ...init, headers })
  if (firstResponse.status !== 401) return firstResponse

  // Получили 401 → пробуем тихий refresh
  const newToken = await silentRefreshAccessToken()
  if (!newToken) return firstResponse

  headers.set('Authorization', `Bearer ${newToken}`)
  return apiFetch(path, { ...init, headers })
}

// ─── Загрузка с прогрессом (XMLHttpRequest) ──────────────────────────────────

/**
 * Загружает `FormData` с колбэком прогресса (`fetch` не умеет отслеживать upload-прогресс).
 * Повторяет логику `authenticatedFetch`: Bearer из стора, тихий refresh при 401.
 * Возвращает объект `Response`, совместимый с `parseJsonOrThrowApi`.
 */
export function authenticatedUploadWithProgress(
  path: string,
  form: FormData,
  onProgress?: (fraction: number) => void,
): Promise<Response> {
  const p = path.startsWith('/') ? path : `/${path}`
  const url = `${API_BASE}${p}`

  const send = (token: string | null): Promise<XMLHttpRequest> =>
    new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest()
      xhr.open('POST', url)
      if (token) xhr.setRequestHeader('Authorization', `Bearer ${token}`)
      xhr.upload.onprogress = (e) => {
        if (onProgress && e.lengthComputable) onProgress(e.loaded / e.total)
      }
      xhr.onload = () => resolve(xhr)
      xhr.onerror = () => reject(new Error('Сетевая ошибка при загрузке файла'))
      xhr.send(form)
    })

  return (async () => {
    const token = useAuthStore.getState().accessToken
    let xhr = await send(token)
    if (xhr.status === 401) {
      const newToken = await silentRefreshAccessToken()
      if (newToken) {
        xhr = await send(newToken)
      }
    }
    return new Response(xhr.responseText, { status: xhr.status, statusText: xhr.statusText })
  })()
}
