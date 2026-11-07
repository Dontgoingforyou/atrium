/**
 * Валидирует URL-путь после логина и возвращает безопасный путь.
 *
 * Разрешает только относительные пути того же origin.
 * Запрещает protocol-relative URLs (//), backslash-redirects (\) и внешние схемы.
 */
export function sanitizeNextPath(next: string): string {
  if (!next) return '/'
  try {
    // Запрещаем явные признаки небезопасного URL
    const trimmed = next.trim()
    if (
      trimmed.startsWith('//') ||
      trimmed.startsWith('\\') ||
      trimmed.includes('\\')
    ) {
      return '/'
    }
    // Разбираем относительно текущего origin
    const url = new URL(trimmed, window.location.origin)
    // Только тот же origin
    if (url.origin !== window.location.origin) {
      return '/'
    }
    return url.pathname + url.search + url.hash
  } catch {
    return '/'
  }
}
