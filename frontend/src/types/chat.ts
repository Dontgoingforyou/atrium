/** Типы чатов, согласованные с Pydantic-схемами бэкенда. */

export type Chat = {
  id: string
  title: string | null
  created_by_sub: string
  created_at: string
  updated_at: string
  /** true — личный диалог (DM) */
  is_direct: boolean
  // Обогащённые поля (заполняются бэкендом при листинге)
  member_subs: string[]
  unread_count: number
  /** Группа — MinIO; DM — signed photo пира */
  avatar_url?: string | null
  avatar_focal_x?: number | null
  avatar_focal_y?: number | null
  /** Версия для CAS (optimistic locking). */
  version: number
}

export type MessageReceipt = 'sent' | 'read'

export type ChatReplyPreview = {
  id: string
  author_sub: string
  body: string
  deleted_for_all_at?: string | null
  quote_text?: string | null
}

export type ChatMessageForwardFrom = {
  author_sub: string
  source_message_id: string | null
}

export type ChatMessageReaction = {
  emoji: string
  count: number
  reacted_by_me: boolean
}

export type ChatAttachment = {
  id: string
  original_filename: string
  content_type: string
  file_size: number
  download_url: string
  created_at: string
  voice_duration_seconds?: number | null
  voice_waveform?: number[] | null
  /** Текст транскрибации голосового сообщения (OpenAI Whisper), если запрошена */
  transcript?: string | null
  /** Сообщение, к которому привязано вложение (для перехода из галереи) */
  message_id?: string | null
}

export type ChatMessage = {
  id: string
  chat_id: string
  author_sub: string
  body: string
  created_at: string
  updated_at: string | null
  deleted_for_all_at: string | null
  /** Только для своих сообщений: отправлено / прочитано (остальными). */
  receipt?: MessageReceipt | null
  attachments?: ChatAttachment[]
  reply_to_message_id?: string | null
  reply_quote_text?: string | null
  reply_to?: ChatReplyPreview | null
  reactions?: ChatMessageReaction[]
  forwarded_from?: ChatMessageForwardFrom | null
  /** Упомянутые участники (sub); с сервера после сохранения */
  mentions?: string[]
  /** Когда сообщение было закреплено (UTC); null/undefined — не закреплено */
  pinned_at?: string | null
  /** Кто закрепил сообщение (sub) */
  pinned_by_sub?: string | null
}

export type MessageReaderItem = {
  user_sub: string
  read_at: string
}

export type MessageReactorItem = {
  user_sub: string
  reacted_at: string
}

export type ChatCreate = {
  title?: string | null
  member_subs?: string[]
}

export type ChatMessageCreate = {
  body: string
  attachment_ids?: string[]
  reply_to_message_id?: string | null
  reply_quote_text?: string | null
  mentions?: string[]
}

export type ChatMessageUpdate = {
  body: string
}

export type { PortalUser, UserPresence } from './user'
