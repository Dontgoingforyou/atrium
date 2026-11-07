import { createChat, listChats, listMessages, postMessage } from '../api/chat/chatApi'
import { tourAnchorSelector } from '../domain/onboarding/guidedTour'
import { waitForTourTarget } from '../utils/guidedTourLayout'

export const TOUR_DEMO_CHAT_TITLE = 'Учебный чат'

export const TOUR_DEMO_MESSAGE_BODY =
  'Это учебное сообщение для онбординга. Правый клик — ответ, реакция или пересылка; «⋯» у сообщения появляется при наведении.'

/** Эмодзи-пасхалка в учебном чате (кнопка мини-игры). */
export const TOUR_DEMO_EMOJI_BODY = '🎮'

const FIRST_CHAT_ROW = tourAnchorSelector('chats-row')

/** Событие: показать контекстное меню для якоря тура (сообщение / строка чата). */
export const GUIDED_TOUR_OPEN_CTX_EVENT = 'guided-tour-open-ctx'

/** Событие: закрыть демо-меню тура (сообщение / строка чата). */
export const GUIDED_TOUR_CLOSE_CTX_EVENT = 'guided-tour-close-ctx'

/** Прокрутить виртуализированный список к учебному сообщению, чтобы якорь попал в DOM. */
export const GUIDED_TOUR_REVEAL_MESSAGE_EVENT = 'guided-tour-reveal-message'

export type GuidedTourOpenCtxDetail = {
  kind: 'message' | 'chat-row'
}

export type GuidedTourRevealMessageDetail = {
  kind: 'text' | 'emoji'
}

export type EnsureTourDemoChatResult =
  | { ok: true; created: boolean; chatId: string; messageEnsured: boolean }
  | { ok: false; reason: string }

type TourMessageLike = {
  body?: string | null
  deleted_for_all_at?: string | null
}

export function isTourDemoTextBody(body: string | null | undefined): boolean {
  return Boolean(body && body === TOUR_DEMO_MESSAGE_BODY)
}

export function isTourDemoEmojiBody(body: string | null | undefined): boolean {
  return Boolean(body && body.trim() === TOUR_DEMO_EMOJI_BODY)
}

/** Индекс учебного текстового сообщения (не чужой поздний чат). */
export function findTourDemoTextIndex(messages: readonly TourMessageLike[]): number {
  for (let i = messages.length - 1; i >= 0; i -= 1) {
    const m = messages[i]
    if (m.deleted_for_all_at) continue
    if (isTourDemoTextBody(m.body)) return i
  }
  return -1
}

/** Индекс учебной 🎮, не любого emoji-only пузыря. */
export function findTourDemoEmojiIndex(messages: readonly TourMessageLike[]): number {
  for (let i = messages.length - 1; i >= 0; i -= 1) {
    const m = messages[i]
    if (m.deleted_for_all_at) continue
    if (isTourDemoEmojiBody(m.body)) return i
  }
  return -1
}

let inFlightDemoChat: Promise<EnsureTourDemoChatResult> | null = null

export function resetTourDemoChatSeed(): void {
  inFlightDemoChat = null
}

export async function ensureGuidedTourDemoChat(
  currentUserSub: string,
  cachedChatId?: string | null,
): Promise<EnsureTourDemoChatResult> {
  if (cachedChatId) {
    return { ok: true, created: false, chatId: cachedChatId, messageEnsured: false }
  }
  if (!inFlightDemoChat) {
    inFlightDemoChat = seedGuidedTourDemoChat(currentUserSub).then((result) => {
      if (!result.ok) {
        inFlightDemoChat = null
      }
      return result
    })
  }
  return inFlightDemoChat
}

async function seedGuidedTourDemoChat(currentUserSub: string): Promise<EnsureTourDemoChatResult> {
  const chats = await listChats({ limit: 100 })
  let chat = chats.find((c) => !c.is_direct && c.title === TOUR_DEMO_CHAT_TITLE)
  let created = false

  if (!chat) {
    chat = await createChat({
      title: TOUR_DEMO_CHAT_TITLE,
      member_subs: [currentUserSub],
    })
    created = true
  }

  const msgs = await listMessages(chat.id, { limit: 80 })
  let messageEnsured = false
  if (findTourDemoTextIndex(msgs) < 0) {
    await postMessage(chat.id, { body: TOUR_DEMO_MESSAGE_BODY })
    messageEnsured = true
  }
  if (findTourDemoEmojiIndex(msgs) < 0) {
    await postMessage(chat.id, { body: TOUR_DEMO_EMOJI_BODY })
    messageEnsured = true
  }

  return { ok: true, created, chatId: chat.id, messageEnsured }
}

export async function waitForTourChatRow(timeoutMs = 5000): Promise<Element | null> {
  return waitForTourTarget(FIRST_CHAT_ROW, timeoutMs, 80)
}

export function dispatchGuidedTourOpenCtx(kind: GuidedTourOpenCtxDetail['kind']): void {
  if (typeof document === 'undefined') return
  document.dispatchEvent(
    new CustomEvent<GuidedTourOpenCtxDetail>(GUIDED_TOUR_OPEN_CTX_EVENT, { detail: { kind } }),
  )
}

export function dispatchGuidedTourCloseCtx(): void {
  if (typeof document === 'undefined') return
  document.dispatchEvent(new CustomEvent(GUIDED_TOUR_CLOSE_CTX_EVENT))
}

export function dispatchGuidedTourRevealMessage(kind: GuidedTourRevealMessageDetail['kind']): void {
  if (typeof document === 'undefined') return
  document.dispatchEvent(
    new CustomEvent<GuidedTourRevealMessageDetail>(GUIDED_TOUR_REVEAL_MESSAGE_EVENT, {
      detail: { kind },
    }),
  )
}

/** Ждёт якорь в виртуализированном списке, периодически прокручивая к учебному сообщению. */
export async function waitForTourChatMessageAnchor(
  kind: GuidedTourRevealMessageDetail['kind'],
  selector: string,
  timeoutMs = 5000,
  pollMs = 80,
): Promise<Element | null> {
  if (typeof document === 'undefined') return null
  const started = Date.now()
  for (;;) {
    dispatchGuidedTourRevealMessage(kind)
    const el = document.querySelector(selector)
    if (el) return el
    if (Date.now() - started >= timeoutMs) return null
    await new Promise((r) => setTimeout(r, pollMs))
  }
}

export {
  stepNeedsTourChatHref,
  stepNeedsTourChatRow,
  stepNeedsTourChatSeed,
} from '../domain/onboarding/guidedTour'
