import { useCallback, useEffect, useRef } from 'react'
import { useQueryClient } from '@tanstack/react-query'

import { API_BASE } from '../../api/rawClient'
import { fetchWsTicket } from '../../hooks/ws/fetchWsTicket'
import { useReconnectingWebSocket } from '../../hooks/ws/useReconnectingWebSocket'
import { toWsUrl } from '../../hooks/ws/url'
import { useAuthStore } from '../../store/authStore'
import { calendarQueryKeys } from './calendarQueryKeys'

const INVALIDATE_DEBOUNCE_MS = 400

/** Real-time обновления календаря: инвалидация списка календарей и occurrences. */
export function useCalendarWebSocket(enabled: boolean) {
  const queryClient = useQueryClient()
  const accessToken = useAuthStore((s) => s.accessToken)
  const invalidateTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    return () => {
      if (invalidateTimerRef.current) clearTimeout(invalidateTimerRef.current)
    }
  }, [])

  const resolveWsUrl = useCallback(async (): Promise<string | null> => {
    const ticket = await fetchWsTicket('/portal/calendar/ws-ticket')
    if (!ticket) return null
    return toWsUrl(API_BASE, `/portal/calendar/ws?ticket=${encodeURIComponent(ticket)}`)
  }, [])

  const onMessage = useCallback(() => {
    if (invalidateTimerRef.current) clearTimeout(invalidateTimerRef.current)
    invalidateTimerRef.current = setTimeout(() => {
      void queryClient.invalidateQueries({ queryKey: calendarQueryKeys.all })
    }, INVALIDATE_DEBOUNCE_MS)
  }, [queryClient])

  useReconnectingWebSocket(Boolean(enabled && accessToken), {
    resolveWsUrl,
    onMessage,
  })
}
