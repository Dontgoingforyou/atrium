import type { ChatMessage, PortalUser } from '../../../types/chat'

export const EMOJI_PICKER_MAX_HEIGHT = 360

export type MessageInputHandle = {
  addFiles: (files: FileList | File[]) => void
}

export type MessageInputProps = {
  chatId: string
  onSend: (
    body: string,
    attachmentIds: string[],
    replyToMessageId?: string | null,
    mentions?: string[],
    replyQuoteText?: string | null,
  ) => Promise<void>
  /** Сообщение, на которое отвечаем (превью над полем ввода). */
  replyTarget?: ChatMessage | null
  /** Выделенный фрагмент при «ответить с цитатой». */
  replyQuoteText?: string | null
  /** Сброс превью ответа (крестик). */
  onClearReply?: () => void
  disabled?: boolean
  /** default — плавающий виджет; panel — /chats; widget — emoji-picker в portal (узкая панель) */
  variant?: 'default' | 'panel' | 'widget'
  /** Участники для @упоминаний (ЛС и группы); пусто — без подсказок */
  mentionUsers?: PortalUser[]
  /** Эфемерные WS-события: печатает / записывает голос. */
  onEphemeralActivity?: (event: 'typing' | 'voice_recording', active: boolean) => void
}
