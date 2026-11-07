import type {
  ChatMessage,
  ChatMessageForwardFrom,
  ChatMessageReaction,
  MessageReceipt,
} from '../../types/chat'
import {
  isEmojiPongEventName,
  parseEmojiPongWsEvent,
  type EmojiPongWsEvent,
} from './emojiPongWs'

export type ChatWsEvent =
  | { type: 'message_created'; message: ChatMessage }
  | { type: 'message_updated'; message: ChatMessage }
  | { type: 'message_deleted'; message: ChatMessage }
  | { type: 'read_state_updated' }
  | { type: 'ignored' }
  | { type: 'members_updated' }
  | { type: 'chat_meta_updated'; chat_id: string; title?: string }
  | { type: 'chat_deleted'; chat_id: string }
  | { type: 'message_reactions_updated'; message_id: string; reactions: ChatMessageReaction[] }
  | { type: 'typing'; user_sub: string; display_name: string; active: boolean }
  | { type: 'voice_recording'; user_sub: string; display_name: string; active: boolean }
  | EmojiPongWsEvent

function parseReceipt(v: unknown): MessageReceipt | null {
  if (v === 'sent' || v === 'read') return v
  return null
}

function normalizeReactions(raw: unknown): ChatMessageReaction[] {
  if (!Array.isArray(raw)) return []
  const out: ChatMessageReaction[] = []
  for (const r of raw) {
    if (!r || typeof r !== 'object') continue
    const o = r as Record<string, unknown>
    const emoji = String(o.emoji ?? '').trim()
    if (!emoji) continue
    const count = Number(o.count ?? 0)
    out.push({
      emoji,
      count: Number.isFinite(count) ? count : 0,
      reacted_by_me: Boolean(o.reacted_by_me),
    })
  }
  return out
}

function isPlainRecord(raw: unknown): raw is Record<string, unknown> {
  return raw != null && typeof raw === 'object' && !Array.isArray(raw)
}

function hasLegacyMessageIds(raw: Record<string, unknown>): boolean {
  return raw.id != null && raw.id !== '' && raw.chat_id != null && raw.chat_id !== ''
}

/** Нормализует DTO сообщения (на случай кэша без новых полей). */
export function normalizeChatMessage(raw: unknown): ChatMessage | null {
  if (!isPlainRecord(raw) || !hasLegacyMessageIds(raw)) return null
  const m = raw
  const rec = parseReceipt(m.receipt)
  const replyRaw = m.reply_to as Record<string, unknown> | null | undefined
  const reply_to =
    replyRaw && replyRaw.id != null
      ? {
          id: String(replyRaw.id),
          author_sub: String(replyRaw.author_sub ?? ''),
          body: String(replyRaw.body ?? ''),
          deleted_for_all_at:
            replyRaw.deleted_for_all_at != null ? String(replyRaw.deleted_for_all_at) : null,
          quote_text:
            replyRaw.quote_text != null && replyRaw.quote_text !== ''
              ? String(replyRaw.quote_text)
              : null,
        }
      : null
  const fwdRaw = m.forwarded_from as Record<string, unknown> | null | undefined
  const forwarded_from: ChatMessageForwardFrom | null =
    fwdRaw && fwdRaw.author_sub != null
      ? {
          author_sub: String(fwdRaw.author_sub),
          source_message_id:
            fwdRaw.source_message_id != null && fwdRaw.source_message_id !== ''
              ? String(fwdRaw.source_message_id)
              : null,
        }
      : null
  return {
    id: String(m.id),
    chat_id: String(m.chat_id),
    author_sub: String(m.author_sub),
    body: m.body != null ? String(m.body) : '',
    created_at: String(m.created_at),
    updated_at: m.updated_at != null ? String(m.updated_at) : null,
    deleted_for_all_at: m.deleted_for_all_at != null ? String(m.deleted_for_all_at) : null,
    receipt: rec,
    attachments: Array.isArray(m.attachments) ? (m.attachments as ChatMessage['attachments']) : undefined,
    reply_to_message_id:
      m.reply_to_message_id != null && m.reply_to_message_id !== ''
        ? String(m.reply_to_message_id)
        : null,
    reply_quote_text:
      m.reply_quote_text != null && m.reply_quote_text !== ''
        ? String(m.reply_quote_text)
        : null,
    reply_to,
    reactions: normalizeReactions(m.reactions),
    forwarded_from,
    pinned_at: m.pinned_at != null ? String(m.pinned_at) : null,
    pinned_by_sub: m.pinned_by_sub != null ? String(m.pinned_by_sub) : null,
  }
}

function isWsEventType(
  s: string,
): s is 'message_created' | 'message_updated' | 'message_deleted' {
  return s === 'message_created' || s === 'message_updated' || s === 'message_deleted'
}

/** Парсит payload WebSocket: envelope `{ event, message }` или плоский legacy-объект. */
export function parseChatWsPayload(raw: unknown): ChatWsEvent {
  if (!isPlainRecord(raw)) {
    return { type: 'ignored' }
  }
  if ('event' in raw) {
    const o = raw as {
      event: string
      message?: unknown
      chat_id?: unknown
      title?: unknown
      message_id?: unknown
      reactions?: unknown
    }
    if (o.event === 'read_state_updated') {
      return { type: 'read_state_updated' }
    }
    if (o.event === 'typing' || o.event === 'voice_recording') {
      const ep = raw as Record<string, unknown>
      return {
        type: o.event,
        user_sub: typeof ep.user_sub === 'string' ? ep.user_sub : '',
        display_name: typeof ep.display_name === 'string' ? ep.display_name : '',
        active: Boolean(ep.active),
      }
    }
    if (isEmojiPongEventName(o.event)) {
      const parsed = parseEmojiPongWsEvent(raw as Record<string, unknown>)
      if (parsed) return parsed
      return { type: 'ignored' }
    }
    if (o.event === 'members_updated') {
      return { type: 'members_updated' }
    }
    if (o.event === 'chat_meta_updated') {
      const chat_id = typeof o.chat_id === 'string' ? o.chat_id : ''
      if (!chat_id) return { type: 'ignored' }
      return {
        type: 'chat_meta_updated',
        chat_id,
        title: typeof o.title === 'string' ? o.title : undefined,
      }
    }
    if (o.event === 'chat_deleted') {
      const chat_id = typeof o.chat_id === 'string' ? o.chat_id : ''
      if (!chat_id) return { type: 'ignored' }
      return {
        type: 'chat_deleted',
        chat_id,
      }
    }
    if (o.event === 'message_reactions_updated') {
      return {
        type: 'message_reactions_updated',
        message_id: typeof o.message_id === 'string' ? o.message_id : String(o.message_id ?? ''),
        reactions: normalizeReactions(o.reactions),
      }
    }
    if (o.message !== undefined && isWsEventType(o.event)) {
      const message = normalizeChatMessage(o.message)
      if (!message) return { type: 'ignored' }
      return { type: o.event, message }
    }
    // envelope с event, но без известного payload — не маскировать под read_state
    return { type: 'ignored' }
  }

  if (!hasLegacyMessageIds(raw)) {
    return { type: 'ignored' }
  }
  const message = normalizeChatMessage(raw)
  if (!message) return { type: 'ignored' }
  return { type: 'message_created', message }
}

/** Для WS без поля `receipt` — для своих сообщений считаем «отправлено». */
export function patchOwnReceiptFromWs(
  list: ChatMessage[],
  e: ChatWsEvent,
  currentUserSub: string | null,
): ChatMessage[] {
  if (
    !currentUserSub
    || e.type === 'read_state_updated'
    || e.type === 'ignored'
    || e.type === 'message_reactions_updated'
    || e.type === 'chat_deleted'
    || !('message' in e)
  ) {
    return list
  }
  if (e.message.author_sub !== currentUserSub) return list
  return list.map((x) =>
    x.id === e.message.id
      ? { ...x, receipt: x.receipt ?? e.message.receipt ?? 'sent' }
      : x,
  )
}

export function applyChatEventToList(prev: ChatMessage[] | undefined, e: ChatWsEvent): ChatMessage[] {
  if (e.type === 'ignored' || e.type === 'read_state_updated') {
    return prev ?? []
  }
  if (e.type === 'message_reactions_updated') {
    if (!prev) return []
    return prev.map((x) =>
      x.id === e.message_id ? { ...x, reactions: e.reactions } : x,
    )
  }
  if (!('message' in e)) {
    return prev ?? []
  }
  if (!prev) {
    if (e.type === 'message_deleted') {
      return []
    }
    return [e.message]
  }
  const m = e.message
  if (e.type === 'message_created') {
    if (prev.some((x) => x.id === m.id)) return prev
    // Убрать optimistic-пузыри того же автора, чтобы не дублировать с ответом HTTP/WS
    const withoutOptimistic = prev.filter(
      (x) => !(x.id.startsWith('optimistic-') && x.author_sub === m.author_sub),
    )
    return [...withoutOptimistic, m]
  }
  if (e.type === 'message_updated') {
    const has = prev.some((x) => x.id === m.id)
    if (has) return prev.map((x) => (x.id === m.id ? m : x))
    return [...prev, m]
  }
  if (e.type === 'message_deleted') {
    return prev.filter((x) => x.id !== m.id)
  }
  return prev
}
