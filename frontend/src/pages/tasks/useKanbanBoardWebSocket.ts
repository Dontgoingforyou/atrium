import { useCallback, useEffect, useRef } from 'react'
import { useQueryClient } from '@tanstack/react-query'

import { API_BASE } from '../../api/rawClient'
import { PORTAL_TASKS_ROOT_QUERY_KEY } from '../../api/queryKeys'
import { useAuthStore } from '../../store/authStore'
import { fetchWsTicket } from '../../hooks/ws/fetchWsTicket'
import { useReconnectingWebSocket } from '../../hooks/ws/useReconnectingWebSocket'
import { toWsUrl } from '../../hooks/ws/url'

const INVALIDATE_DEBOUNCE_MS = 400

/**
 * Подключается к WS доски задач и инвалидирует React Query кэш при каждом событии.
 * Открывается только в режиме канбана (`enabled`).
 */
export function useKanbanBoardWebSocket(enabled: boolean) {
  const queryClient = useQueryClient()
  const accessToken = useAuthStore((s) => s.accessToken)
  const invalidateTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    return () => {
      if (invalidateTimerRef.current) clearTimeout(invalidateTimerRef.current)
    }
  }, [])

  const resolveWsUrl = useCallback(async (): Promise<string | null> => {
    const ticket = await fetchWsTicket('/portal/tasks/board/ws-ticket')
    if (!ticket) return null
    return toWsUrl(API_BASE, `/portal/tasks/board/ws?ticket=${encodeURIComponent(ticket)}`)
  }, [])

  const onMessage = useCallback(() => {
    if (invalidateTimerRef.current) clearTimeout(invalidateTimerRef.current)
    invalidateTimerRef.current = setTimeout(() => {
      void queryClient.invalidateQueries({ queryKey: PORTAL_TASKS_ROOT_QUERY_KEY })
    }, INVALIDATE_DEBOUNCE_MS)
  }, [queryClient])

  useReconnectingWebSocket(Boolean(enabled && accessToken), {
    resolveWsUrl,
    onMessage,
  })
}
