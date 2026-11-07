/** Кратковременный bearer для /docs и /redoc (страницы вне React, без zustand в памяти). */
export const PORTAL_DOCS_TOKEN_KEY = 'portal_docs_token'

export function stashDocsBearerToken(accessToken: string | null | undefined): void {
  if (!accessToken) return
  try {
    sessionStorage.setItem(PORTAL_DOCS_TOKEN_KEY, accessToken)
  } catch {
    /* ignore quota / private mode */
  }
}

/** Очистка bearer-токена /docs из sessionStorage — вызывается при logout/clearSession, чтобы
 *  устаревший токен не оставался в хранилище после выхода. */
export function clearDocsBearerToken(): void {
  try {
    sessionStorage.removeItem(PORTAL_DOCS_TOKEN_KEY)
  } catch {
    /* ignore quota / private mode */
  }
}
