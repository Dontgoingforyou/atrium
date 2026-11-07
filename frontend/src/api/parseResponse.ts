import { userFacingMessageFromApiFailure } from '../utils/apiUserMessage'
import { ApiConflictError } from './apiConflict'

function extractApiCode(bodyText: string): string | undefined {
  const trimmed = bodyText.trim()
  if (!trimmed) return undefined
  try {
    const parsed: unknown = JSON.parse(trimmed)
    if (!parsed || typeof parsed !== 'object') return undefined
    const code = (parsed as { code?: unknown }).code
    return typeof code === 'string' ? code : undefined
  } catch {
    return undefined
  }
}

/**
 * Читает тело ответа; при !res.ok бросает Error с пользовательским текстом.
 * 409 + code=conflict → {@link ApiConflictError}.
 * Пустое тело при успехе → undefined (удобно для 204).
 */
export async function parseJsonOrThrowApi<T>(res: Response): Promise<T> {
  const text = await res.text()
  if (!res.ok) {
    const message = userFacingMessageFromApiFailure(res.status, text)
    if (res.status === 409 && extractApiCode(text) === 'conflict') {
      throw new ApiConflictError(message)
    }
    throw new Error(message)
  }
  if (!text) {
    return undefined as T
  }
  return JSON.parse(text) as T
}
