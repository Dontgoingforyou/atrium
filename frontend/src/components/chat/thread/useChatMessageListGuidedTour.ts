import { useEffect, type RefObject } from 'react'
import type { Virtualizer } from '@tanstack/react-virtual'

import type { ChatMessage } from '../../../types/chat'
import type { MenuState } from './MessageContextMenu'
import {
  findTourDemoEmojiIndex,
  findTourDemoTextIndex,
  GUIDED_TOUR_CLOSE_CTX_EVENT,
  GUIDED_TOUR_OPEN_CTX_EVENT,
  GUIDED_TOUR_REVEAL_MESSAGE_EVENT,
  type GuidedTourOpenCtxDetail,
  type GuidedTourRevealMessageDetail,
} from '../../../onboarding/ensureTourDemoChat'

type Args = {
  messagesRef: RefObject<ChatMessage[]>
  virtualizerRef: RefObject<Virtualizer<HTMLDivElement, Element>>
  containerRef: RefObject<HTMLDivElement | null>
  setMenu: (menu: MenuState | null) => void
  setActionError: (err: string | null) => void
}

/**
 * Проводка событий guided-tour в ленту сообщений:
 *  - REVEAL_MESSAGE — прокрутка к демо-сообщению (текст/emoji);
 *  - OPEN_CTX/CLOSE_CTX — открытие/закрытие контекстного меню по требованию тура.
 *
 * Слушатели навешиваются один раз на mount; актуальные данные берутся из ref'ов.
 */
export function useChatMessageListGuidedTour({
  messagesRef,
  virtualizerRef,
  containerRef,
  setMenu,
  setActionError,
}: Args) {
  useEffect(() => {
    function onReveal(ev: Event) {
      const kind = (ev as CustomEvent<GuidedTourRevealMessageDetail>).detail?.kind
      const list = messagesRef.current
      const idx =
        kind === 'emoji' ? findTourDemoEmojiIndex(list) : findTourDemoTextIndex(list)
      if (idx < 0) return
      virtualizerRef.current.scrollToIndex(idx, { align: 'center' })
    }
    document.addEventListener(GUIDED_TOUR_REVEAL_MESSAGE_EVENT, onReveal)
    return () => document.removeEventListener(GUIDED_TOUR_REVEAL_MESSAGE_EVENT, onReveal)
  }, [messagesRef, virtualizerRef])

  useEffect(() => {
    function onTourOpenCtx(ev: Event) {
      const detail = (ev as CustomEvent<GuidedTourOpenCtxDetail>).detail
      if (detail?.kind !== 'message') return
      const list = messagesRef.current
      if (!list.length) return
      const tourIdx = findTourDemoTextIndex(list)
      const msg = list[tourIdx >= 0 ? tourIdx : list.length - 1]
      const row = containerRef.current?.querySelector<HTMLElement>(
        `[data-message-id="${msg.id}"]`,
      )
      const bubble = row?.querySelector<HTMLElement>('[data-msg-body]')
      const anchor = bubble?.closest('div') ?? row
      const r = anchor?.getBoundingClientRect()
      if (!r) return
      setActionError(null)
      setMenu({
        x: Math.min(r.left + 12, window.innerWidth - 260),
        y: Math.min(r.bottom + 4, window.innerHeight - 200),
        message: msg,
        selectedQuote: null,
      })
    }
    function onTourCloseCtx() {
      setMenu(null)
    }
    document.addEventListener(GUIDED_TOUR_OPEN_CTX_EVENT, onTourOpenCtx)
    document.addEventListener(GUIDED_TOUR_CLOSE_CTX_EVENT, onTourCloseCtx)
    return () => {
      document.removeEventListener(GUIDED_TOUR_OPEN_CTX_EVENT, onTourOpenCtx)
      document.removeEventListener(GUIDED_TOUR_CLOSE_CTX_EVENT, onTourCloseCtx)
    }
  }, [containerRef, messagesRef, setMenu, setActionError])
}
