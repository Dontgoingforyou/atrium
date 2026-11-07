import type { Chat } from '../../types/chat'

export function dmPeerSub(chat: Chat, currentSub: string | null): string | null {
  if (!chat.is_direct || !currentSub) return null
  if (!chat.member_subs.includes(currentSub)) return null
  return chat.member_subs.find((s) => s !== currentSub) ?? null
}
