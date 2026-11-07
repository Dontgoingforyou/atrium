/**
 * Утилита для безопасного открытия внешних ссылок.
 *
 * Проблема: если передавать URL напрямую в window.open или href без проверки,
 * злоумышленник может подсунуть «javascript:» или «data:» URL → XSS.
 * Дополнительно — ограничиваем домены allowlist'ом для бизнес-логики.
 */

/** Разрешённые внешние домены (полные hostname или суффиксы через точку). */
const ALLOWED_EXTERNAL_HOSTS: readonly string[] = [
  't.me',
  'telegram.me',
  'telegram.org',
]

/** Разрешённые схемы для внешних URL. */
const ALLOWED_SCHEMES: readonly string[] = ['https:', 'http:']

/**
 * Проверить, что URL безопасен для открытия.
 *
 * - Принимает только https: и http:
 * - Опционально — только из ALLOWED_EXTERNAL_HOSTS (при `restrictToAllowlist = true`)
 */
export function isSafeExternalUrl(
  rawUrl: string,
  options: { restrictToAllowlist?: boolean } = {},
): boolean {
  let url: URL
  try {
    url = new URL(rawUrl)
  } catch {
    return false
  }

  if (!ALLOWED_SCHEMES.includes(url.protocol)) {
    return false
  }

  if (options.restrictToAllowlist) {
    const host = url.hostname.toLowerCase()
    const allowed = ALLOWED_EXTERNAL_HOSTS.some(
      (domain) => host === domain || host.endsWith(`.${domain}`),
    )
    if (!allowed) return false
  }

  return true
}

/**
 * Вернуть URL, только если он безопасен; иначе вернуть undefined.
 * Удобна для использования в JSX: href={safeExternalUrl(link)}.
 */
export function safeExternalUrl(
  rawUrl: string | null | undefined,
  options?: { restrictToAllowlist?: boolean },
): string | undefined {
  if (!rawUrl) return undefined
  return isSafeExternalUrl(rawUrl, options) ? rawUrl : undefined
}

/**
 * Открыть внешнюю ссылку в новой вкладке с rel="noopener noreferrer".
 * Если URL небезопасен — ничего не делает и возвращает false.
 */
export function openExternalUrl(
  rawUrl: string,
  options?: { restrictToAllowlist?: boolean },
): boolean {
  if (!isSafeExternalUrl(rawUrl, options)) {
    return false
  }
  const win = window.open(rawUrl, '_blank', 'noopener,noreferrer')
  if (win) win.opener = null
  return true
}
