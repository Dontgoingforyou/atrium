import { useCallback, useEffect, useRef } from 'react'
import { useQueryClient } from '@tanstack/react-query'

import { API_BASE } from '../../api/rawClient'
import { useAuthStore } from '../../store/authStore'
import { fetchWsTicket } from '../../hooks/ws/fetchWsTicket'
import { useReconnectingWebSocket } from '../../hooks/ws/useReconnectingWebSocket'
import { toWsUrl } from '../../hooks/ws/url'
import {
  SPECIALISTS_DETAIL_ROOT_QUERY_KEY,
  SPECIALISTS_LIST_QUERY_KEY,
  SPECIALISTS_STUDENTS_ROOT_QUERY_KEY,
  specialistStudentsModalQueryKey,
} from './specialistQueryKeys'

const INVALIDATE_DEBOUNCE_MS = 400

/** Real-time: инвалидация кэша доски и карточек специалистов при изменениях у других пользователей. */
export function useSpecialistsBoardWebSocket(enabled: boolean) {
  const queryClient = useQueryClient()
  const accessToken = useAuthStore((s) => s.accessToken)
  const invalidateTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    return () => {
      if (invalidateTimerRef.current) clearTimeout(invalidateTimerRef.current)
    }
  }, [])

  const resolveWsUrl = useCallback(async (): Promise<string | null> => {
    const ticket = await fetchWsTicket('/portal/specialists/board/ws-ticket')
    if (!ticket) return null
    return toWsUrl(
      API_BASE,
      `/portal/specialists/board/ws?ticket=${encodeURIComponent(ticket)}`,
    )
  }, [])

  const onMessage = useCallback(() => {
    if (invalidateTimerRef.current) clearTimeout(invalidateTimerRef.current)
    invalidateTimerRef.current = setTimeout(() => {
      void queryClient.invalidateQueries({ queryKey: SPECIALISTS_LIST_QUERY_KEY })
      void queryClient.invalidateQueries({ queryKey: SPECIALISTS_DETAIL_ROOT_QUERY_KEY })
      void queryClient.invalidateQueries({ queryKey: SPECIALISTS_STUDENTS_ROOT_QUERY_KEY })
      void queryClient.invalidateQueries({ queryKey: specialistStudentsModalQueryKey() })
    }, INVALIDATE_DEBOUNCE_MS)
  }, [queryClient])

  useReconnectingWebSocket(Boolean(enabled && accessToken), {
    resolveWsUrl,
    onMessage,
  })
}
