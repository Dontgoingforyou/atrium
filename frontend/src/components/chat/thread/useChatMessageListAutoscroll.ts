import {
  useLayoutEffect,
  useRef,
  useEffect,
  type MutableRefObject,
  type RefObject,
} from 'react'
import type { Virtualizer } from '@tanstack/react-virtual'
import type { ChatMessage } from '../../../types/chat'

const STICK_TO_BOTTOM_PX = 80

function isNearBottom(el: HTMLElement, thresholdPx: number): boolean {
  return el.scrollHeight - el.scrollTop - el.clientHeight <= thresholdPx
}

/** Плавный скролл к сообщению, если пользователь не отключил motion. */
function scrollBehaviorForJump(): ScrollBehavior {
  if (typeof window === 'undefined') return 'auto'
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth'
}

type Args = {
  chatId: string
  messages: ChatMessage[]
  messagesRef: MutableRefObject<ChatMessage[]>
  containerRef: RefObject<HTMLDivElement | null>
  virtualizer: Virtualizer<HTMLDivElement, Element>
  isEmpty: boolean
  currentUserSub: string | null
  editingId: string | null | undefined
  effectiveScrollToMessageId: string | null
  localJumpId: string | null
  setLocalJumpId: (id: string | null) => void
  onDeepLinkScrollConsumedRef: MutableRefObject<(() => void) | undefined>
}

export function useChatMessageListAutoscroll({
  chatId,
  messages,
  messagesRef,
  containerRef,
  virtualizer,
  isEmpty,
  currentUserSub,
  editingId,
  effectiveScrollToMessageId,
  localJumpId,
  setLocalJumpId,
  onDeepLinkScrollConsumedRef,
}: Args) {
  const consumedDeepLinkRef = useRef<string | null>(null)
  const initialBottomScrollChatRef = useRef<string | null>(null)
  const stuckToBottomRef = useRef(true)
  const prevMessagesLenRef = useRef(0)
  const prevLastMessageIdRef = useRef<string | null>(null)
  const prevLastReactionsFpRef = useRef<string>('')
  const lastMessage = messages[messages.length - 1]
  const lastMessageId = lastMessage?.id
  const lastMessageReactions = lastMessage?.reactions

  useEffect(() => {
    consumedDeepLinkRef.current = null
    initialBottomScrollChatRef.current = null
    stuckToBottomRef.current = true
    prevMessagesLenRef.current = 0
    prevLastMessageIdRef.current = null
    prevLastReactionsFpRef.current = ''
    setLocalJumpId(null)
  }, [chatId, setLocalJumpId])

  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    const onScroll = () => {
      stuckToBottomRef.current = isNearBottom(el, STICK_TO_BOTTOM_PX)
    }
    el.addEventListener('scroll', onScroll, { passive: true })
    return () => el.removeEventListener('scroll', onScroll)
  }, [chatId, isEmpty, containerRef])

  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    const ro = new ResizeObserver(() => {
      if (!stuckToBottomRef.current) return
      virtualizer.scrollToIndex(messagesRef.current.length - 1, { align: 'end' })
    })
    ro.observe(el)
    return () => ro.disconnect()
    // eslint-disable-next-line react-hooks/exhaustive-deps -- virtualizer нестабилен
  }, [chatId, isEmpty, containerRef, messagesRef])

  useLayoutEffect(() => {
    const list = messagesRef.current
    if (list.length === 0) return

    const scrollToEnd = () => {
      virtualizer.scrollToIndex(list.length - 1, { align: 'end' })
      stuckToBottomRef.current = true
    }

    // Клик по цитате/ответу: отдельно от deeplink (consumedDeepLinkRef),
    // иначе повторный клик на тот же id блокировал автоскролл ленты.
    // Сбрасываем localJumpId только после успешного скролла; miss ждёт
    // догрузки списка (сброс при смене chatId — в ChatMessageList).
    if (localJumpId) {
      const idx = list.findIndex((m) => m.id === localJumpId)
      if (idx >= 0) {
        virtualizer.scrollToIndex(idx, {
          align: 'center',
          behavior: scrollBehaviorForJump(),
        })
        stuckToBottomRef.current = false
        setLocalJumpId(null)
      }
      return
    }

    if (effectiveScrollToMessageId) {
      if (consumedDeepLinkRef.current !== effectiveScrollToMessageId) {
        const idx = list.findIndex((m) => m.id === effectiveScrollToMessageId)
        if (idx >= 0) {
          virtualizer.scrollToIndex(idx, {
            align: 'center',
            behavior: scrollBehaviorForJump(),
          })
          consumedDeepLinkRef.current = effectiveScrollToMessageId
          stuckToBottomRef.current = false
          onDeepLinkScrollConsumedRef.current?.()
          return
        }
        consumedDeepLinkRef.current = effectiveScrollToMessageId
        onDeepLinkScrollConsumedRef.current?.()
        scrollToEnd()
        requestAnimationFrame(() => requestAnimationFrame(scrollToEnd))
        return
      }
      return
    }

    const needsInitialOpenScroll = initialBottomScrollChatRef.current !== chatId
    if (needsInitialOpenScroll) {
      initialBottomScrollChatRef.current = chatId
      scrollToEnd()
      requestAnimationFrame(() => requestAnimationFrame(scrollToEnd))
      prevMessagesLenRef.current = list.length
      prevLastMessageIdRef.current = list[list.length - 1]?.id ?? null
      const last = list[list.length - 1]
      prevLastReactionsFpRef.current = last
        ? `${last.id}:${(last.reactions ?? []).map((r) => `${r.emoji}${r.count}`).join(',')}`
        : ''
      return
    }

    const lastId = list[list.length - 1]?.id ?? null
    const prevLen = prevMessagesLenRef.current
    const prevLastId = prevLastMessageIdRef.current
    prevMessagesLenRef.current = list.length
    prevLastMessageIdRef.current = lastId

    const last = list[list.length - 1]
    const reactionsFp = last
      ? `${last.id}:${(last.reactions ?? []).map((r) => `${r.emoji}${r.count}`).join(',')}`
      : ''
    const reactionsGrew = reactionsFp !== prevLastReactionsFpRef.current
    prevLastReactionsFpRef.current = reactionsFp

    const appended =
      list.length > prevLen && lastId !== null && lastId !== prevLastId
    if (!appended && !(reactionsGrew && stuckToBottomRef.current)) return

    const isOwn = Boolean(currentUserSub && last?.author_sub === currentUserSub)
    if (stuckToBottomRef.current || isOwn) {
      scrollToEnd()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- virtualizer нестабилен
  }, [
    chatId,
    messages.length,
    editingId,
    effectiveScrollToMessageId,
    currentUserSub,
    localJumpId,
    lastMessageId,
    lastMessageReactions,
  ])
}
