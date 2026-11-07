import type { Chat } from '../../types/chat'

/** DM — любой участник; группа — только создатель (согласовано с API). */
export function canDeleteEntireChat(chat: Chat, currentUserSub: string | null): boolean {
  if (!currentUserSub) return false
  if (!chat.member_subs.includes(currentUserSub)) return false
  if (chat.is_direct) return true
  return chat.created_by_sub === currentUserSub
}
