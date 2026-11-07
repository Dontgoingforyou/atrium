/** Серверный keepalive: JSON ``{"type":"ping"}`` / ответ ``{"type":"pong"}``. */

export const WS_PONG_MESSAGE = JSON.stringify({ type: 'pong' })

export function isWsPing(data: unknown): boolean {
  if (typeof data !== 'string') return false
  try {
    const parsed: unknown = JSON.parse(data)
    return (
      typeof parsed === 'object' &&
      parsed !== null &&
      'type' in parsed &&
      (parsed as { type: unknown }).type === 'ping'
    )
  } catch {
    return false
  }
}
