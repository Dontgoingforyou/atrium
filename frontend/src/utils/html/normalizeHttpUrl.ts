/**
 * Нормализует пользовательский ввод URL для внешних ссылок.
 * Домен без схемы (например qualify.su) дополняется https://;
 * схемы кроме http/https отклоняются (XSS через javascript:/data:).
 */
export function normalizeHttpUrl(raw: string): string | null {
  const trimmed = raw.trim()
  if (!trimmed) return ''
  if (trimmed.startsWith('//')) return null
  try {
    const u = new URL(trimmed.includes('://') ? trimmed : `https://${trimmed}`)
    if (u.protocol !== 'https:' && u.protocol !== 'http:') return null
    return u.href
  } catch {
    return null
  }
}
