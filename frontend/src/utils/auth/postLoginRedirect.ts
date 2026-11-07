import type { NavigateFunction } from 'react-router'

import { stashDocsBearerToken } from '../../constants/docsAuth'
import { sanitizeNextPath } from './safeRedirect'

/** Путь SQLAdmin (не путать с SPA `/admin-bridge`). */
export function isAdminPanelPath(path: string): boolean {
  return path === '/admin' || path.startsWith('/admin/')
}

/** OpenAPI / ReDoc вне React — нужен stash access-токена в sessionStorage. */
export function isDocsOrRedocPath(path: string): boolean {
  return (
    path === '/docs' ||
    path.startsWith('/docs/') ||
    path.startsWith('/docs#') ||
    path === '/redoc' ||
    path.startsWith('/redoc/') ||
    path.startsWith('/redoc#')
  )
}

/**
 * Редирект после успешного логина / OAuth exchange.
 *
 * - `/docs`, `/redoc` — full reload + stash bearer (исключение security.mdc)
 * - `/admin`, `/admin/`… — SPA `/admin-bridge` (cookie-сессия), без stash
 * - остальное — SPA navigate
 */
export function goToPostLoginPath(
  path: string,
  accessToken: string | null | undefined,
  navigate: NavigateFunction,
): void {
  const nextPath = sanitizeNextPath(path)
  if (isAdminPanelPath(nextPath)) {
    navigate('/admin-bridge', { replace: true })
    return
  }
  if (isDocsOrRedocPath(nextPath)) {
    stashDocsBearerToken(accessToken)
    window.location.href = nextPath
    return
  }
  navigate(nextPath, { replace: true })
}
