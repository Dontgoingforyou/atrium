import { useEffect, useRef } from 'react'

import { isWsPing, WS_PONG_MESSAGE } from '../../utils/wsPing'
import { WS_BASE_DELAY_MS, WS_JITTER_RATIO, WS_MAX_DELAY_MS } from './constants'

export type ReconnectingWebSocketHandlers = {
  /** Вернуть полный WS URL или ``null`` для повторной попытки после backoff. */
  resolveWsUrl: () => Promise<string | null>
  onMessage: (event: MessageEvent) => void
  onOpen?: (ws: WebSocket) => void
}

/**
 * WebSocket с автоматическим reconnect и exponential backoff.
 * Ticket-flow и разбор payload — на стороне ``resolveWsUrl`` / ``onMessage``.
 *
 * @param connectionKey — смена ключа (например chatId) принудительно переоткрывает сокет.
 */
export function useReconnectingWebSocket(
  enabled: boolean,
  handlers: ReconnectingWebSocketHandlers,
  connectionKey: string | null = null,
): void {
  const handlersRef = useRef(handlers)
  useEffect(() => {
    handlersRef.current = handlers
  })

  useEffect(() => {
    if (!enabled) return

    let ws: WebSocket | null = null
    let retryTimer: ReturnType<typeof setTimeout> | null = null
    let stopped = false
    let retryDelay = WS_BASE_DELAY_MS
    /** Инкремент при cleanup — отбрасывает in-flight connect после await ticket. */
    let connectGen = 0

    function scheduleRetry(): void {
      if (stopped) return
      if (retryTimer) clearTimeout(retryTimer)
      const jitter = retryDelay * WS_JITTER_RATIO
      const delay = retryDelay - jitter + Math.random() * jitter * 2
      retryTimer = setTimeout(() => {
        if (!stopped) void connect()
      }, delay)
      retryDelay = Math.min(retryDelay * 2, WS_MAX_DELAY_MS)
    }

    async function connect(): Promise<void> {
      if (stopped) return
      const gen = ++connectGen
      let url: string | null
      try {
        url = await handlersRef.current.resolveWsUrl()
      } catch {
        if (!stopped && gen === connectGen) scheduleRetry()
        return
      }
      // После await эффект мог уже размонтироваться / перезапуститься
      if (stopped || gen !== connectGen) return
      if (url === null) {
        scheduleRetry()
        return
      }
      try {
        ws = new WebSocket(url)
      } catch {
        if (!stopped && gen === connectGen) scheduleRetry()
        return
      }

      const socket = ws
      socket.onopen = () => {
        if (stopped || gen !== connectGen) {
          try {
            socket.close()
          } catch {
            // ignore
          }
          return
        }
        retryDelay = WS_BASE_DELAY_MS
        handlersRef.current.onOpen?.(socket)
      }

      socket.onmessage = (event: MessageEvent) => {
        if (stopped || gen !== connectGen) return
        if (isWsPing(event.data)) {
          if (socket.readyState === WebSocket.OPEN) {
            try {
              socket.send(WS_PONG_MESSAGE)
            } catch {
              // сокет мог уйти в CLOSING/CLOSED между проверкой и send
            }
          }
          return
        }
        handlersRef.current.onMessage(event)
      }

      socket.onerror = () => {
        // обычно дальше onclose
      }

      socket.onclose = () => {
        if (stopped || gen !== connectGen) return
        if (ws === socket) ws = null
        scheduleRetry()
      }
    }

    void connect()

    return () => {
      stopped = true
      connectGen += 1
      if (retryTimer) clearTimeout(retryTimer)
      const toClose = ws
      ws = null
      if (toClose) {
        try {
          toClose.close()
        } catch {
          // ignore
        }
      }
    }
  }, [enabled, connectionKey])
}
