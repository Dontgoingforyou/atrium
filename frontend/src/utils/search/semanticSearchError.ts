import { userFacingMessageFromUnknown } from '../apiUserMessage'
import type { PortalSearchMode } from '@/types/search'

/** Только 503 «ключ не задан»; ошибки SQL/OpenAI (500) показываем как обычную ошибку. */
export function isSemanticUnavailableError(err: unknown): boolean {
  const msg = userFacingMessageFromUnknown(err)
  return msg.includes('OPENAI_API_KEY не задан') || msg.includes('Семантический поиск недоступен')
}

/** `mode === 'semantic'` → semantic, иначе fulltext. */
export function parseSearchMode(raw: string | null): PortalSearchMode {
  return raw === 'semantic' ? 'semantic' : 'fulltext'
}
