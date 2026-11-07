import { useCallback, useEffect, useRef } from 'react'

import { API_BASE } from '../api/rawClient'
import { useAuthStore } from '../store/authStore'
import type { ChatWsEvent } from '@/utils/chat/chatWs'
import { parseChatWsPayload } from '@/utils/chat/chatWs'
import { fetchWsTicket } from './ws/fetchWsTicket'
import { useReconnectingWebSocket } from './ws/useReconnectingWebSocket'
import { toWsUrl } from './ws/url'

export type ChatWsSendJson = (payload: Record<string, unknown>) => void

type Options = {
  /** Событие чата (новое/изменённое/удалённое сообщение); legacy-плоский JSON мапится на message_created */
  onEvent: (e: ChatWsEvent) => void
  /** Вызывается при ошибке соединения */
  onError?: (error: Event) => void
  /** Вызывается при каждом успешном подключении WS (в т.ч. после reconnect). */
  onConnection?: (sendJson: ChatWsSendJson) => void
}

/**
 * Хук для подключения к WebSocket чата.
 * Reconnect — через общий ``useReconnectingWebSocket``.
 */
export function useChatWebSocket(chatId: string | null, { onEvent, onError, onConnection }: Options): void {
  const accessToken = useAuthStore((s) => s.accessToken)
  const onEventRef = useRef<(e: ChatWsEvent) => void>(onEvent)
  const onErrorRef = useRef<((error: Event) => void) | undefined>(onError)
  const onConnectionRef = useRef<((sendJson: ChatWsSendJson) => void) | undefined>(onConnection)
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    onEventRef.current = onEvent
    onErrorRef.current = onError
    onConnectionRef.current = onConnection
  })

  const resolveWsUrl = useCallback(async (): Promise<string | null> => {
    if (!chatId) return null
    const ticket = await fetchWsTicket(`/portal/chats/${encodeURIComponent(chatId)}/ws-ticket`)
    if (!ticket) {
      onErrorRef.current?.(new Event('ws-ticket'))
      return null
    }
    return toWsUrl(
      API_BASE,
      `/portal/chats/${encodeURIComponent(chatId)}/ws?ticket=${encodeURIComponent(ticket)}`,
    )
  }, [chatId])

  const onMessage = useCallback((event: MessageEvent) => {
    try {
      const raw = JSON.parse(event.data as string) as unknown
      const e = parseChatWsPayload(raw)
      onEventRef.current(e)
    } catch {
      // некорректный JSON — игнорируем
    }
  }, [])

  /** Стабильная отправка: всегда в актуальный сокет из wsRef. */
  const sendJson = useCallback<ChatWsSendJson>((payload) => {
    const socket = wsRef.current
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify(payload))
    }
  }, [])

  const onOpen = useCallback((ws: WebSocket) => {
    wsRef.current = ws
    onConnectionRef.current?.(sendJson)
  }, [sendJson])

  useEffect(() => {
    if (!chatId) {
      wsRef.current = null
    }
  }, [chatId])

  useReconnectingWebSocket(
    Boolean(chatId && accessToken),
    {
      resolveWsUrl,
      onMessage,
      onOpen,
    },
    chatId,
  )
}
