import { sanitizeNextPath } from './safeRedirect'

/**
 * Правило фильтрации пути для post-login redirect (`auth_next`).
 *
 * Пути `/login` и `/auth/*` (OAuth callback) не имеют смысла как цель возврата
 * после входа — сохранение такого пути привело бы к редирект-циклу. Используется
 * в `RequireAuth` при записи `sessionStorage.auth_next`.
 */
export function shouldSaveAuthNextPath(path: string): boolean {
  if (path === '/login' || path.startsWith('/login?') || path.startsWith('/login#')) return false
  if (path.startsWith('/auth/')) return false
  return true
}

/**
 * Разобрать `?next=` на странице логина.
 *
 * Пустой / отсутствующий query **не** считается целью — иначе `sanitizeNextPath('')`
 * даёт `/` и затирает путь, который `RequireAuth` уже положил в `auth_next`.
 * Возвращает санитизированный путь или `null`, если писать в storage не нужно.
 */
export function resolveLoginNextQueryParam(rawNext: string | null | undefined): string | null {
  if (rawNext == null || rawNext.trim() === '') return null
  const sanitized = sanitizeNextPath(rawNext)
  if (!shouldSaveAuthNextPath(sanitized)) return null
  return sanitized
}
