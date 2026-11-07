/**
 * Единая формулировка ошибок API для показа пользователю (без сырого тела 5xx и сетевого шума).
 * Тело ошибок FastAPI см. backend/app/api/exception_handlers.py (поля code, message).
 */

const GENERIC_SERVER = 'Сервис временно недоступен. Попробуйте позже.'
const GENERIC_NETWORK = 'Не удалось связаться с сервером. Проверьте сеть.'
const GENERIC_UNKNOWN = 'Произошла непредвиденная ошибка.'

function extractBackendHint(bodyText: string): string | undefined {
  const trimmed = bodyText.trim()
  if (!trimmed) return undefined
  try {
    const parsed: unknown = JSON.parse(trimmed)
    if (!parsed || typeof parsed !== 'object') return undefined
    const o = parsed as Record<string, unknown>
    if (typeof o.message === 'string' && o.message.trim()) {
      return o.message.trim()
    }
    if (typeof o.detail === 'string' && o.detail.trim()) {
      return o.detail.trim()
    }
    if (Array.isArray(o.detail)) {
      const parts = o.detail
        .map((item) => {
          if (typeof item === 'string') return item
          if (item && typeof item === 'object' && 'msg' in item) {
            const msg = (item as { msg?: unknown }).msg
            return typeof msg === 'string' ? msg : null
          }
          return null
        })
        .filter((x): x is string => Boolean(x))
      if (parts.length) return parts.join(' ')
    }
  } catch {
    /* не JSON — оставляем undefined */
  }
  return undefined
}

/**
 * Сообщение для UI из HTTP-ответа с ошибкой (текст тела уже прочитан).
 */
export function userFacingMessageFromApiFailure(status: number, bodyText: string): string {
  const hint = extractBackendHint(bodyText)

  if (status >= 500) {
    // Бэкенд отдаёт осмысленный message (например 503 при недоступном SSO) — показываем его вместо общей фразы.
    return hint ?? GENERIC_SERVER
  }

  if (status === 401) {
    return hint ?? 'Сессия истекла. Войдите снова.'
  }
  if (status === 403) {
    return hint ?? 'Недостаточно прав для этого действия.'
  }
  if (status === 404) {
    return hint ?? 'Запрошенные данные не найдены.'
  }
  if (hint) {
    return hint
  }
  return `Запрос не выполнен (${status}).`
}

/**
 * Сообщение для UI из неизвестной ошибки (в т.ч. TanStack Query / fetch).
 */
export function userFacingMessageFromUnknown(error: unknown): string {
  if (error instanceof Error) {
    const { message, name } = error
    if (name === 'TypeError' || message === 'Failed to fetch' || message.includes('NetworkError')) {
      return GENERIC_NETWORK
    }
    if (message) {
      return message
    }
  }
  return GENERIC_UNKNOWN
}
