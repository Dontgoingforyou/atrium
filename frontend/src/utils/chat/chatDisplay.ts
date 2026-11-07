import type { Chat } from '../../types/chat'
import { dmPeerSub } from './dmPeerSub'

/** Отображаемое имя чата: DM — собеседник; иначе заголовок. */
export function chatDisplayName(
  chat: Chat,
  currentSub: string | null,
  userMap: Record<string, string>,
): string {
  if (chat.is_direct) {
    const other = dmPeerSub(chat, currentSub)
    if (other) return userMap[other] ?? '...'
    return chat.title ?? '(без названия)'
  }
  return chat.title ?? '(без названия)'
}
