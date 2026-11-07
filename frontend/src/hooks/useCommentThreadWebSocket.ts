import { useQueryClient, type QueryKey } from '@tanstack/react-query'
import { useEffect, useRef } from 'react'

import { API_BASE } from '../api/rawClient'
import { COMMENT_THREAD_UPDATED_EVENT } from '../domain/comments/commentThreadEvents'
import { documentCommentsQueryKey } from '../utils/documents/documentNavigation'
import { taskCommentsQueryKey } from '../pages/tasks/tasksQueryKeys'
import { fetchWsTicket } from './ws/fetchWsTicket'
import { toWsUrl } from './ws/url'
import { useReconnectingWebSocket } from './ws/useReconnectingWebSocket'

type ThreadWsPayload = { event: string }

function isThreadPayload(raw: unknown): raw is ThreadWsPayload {
  return (
    raw !== null &&
    typeof raw === 'object' &&
    'event' in raw &&
    typeof (raw as ThreadWsPayload).event === 'string'
  )
}

/**
 * WebSocket к «комнате» треда комментариев (задача, документ) — refetch кэша при ``thread_updated``.
 * ``pathPrefix`` — база без /ws, например ``/portal/tasks/{id}/comments`` или ``/portal/documents/{id}/comments``.
 */
function useCommentThreadResourceWebSocket(pathPrefix: string | null, queryKey: QueryKey, enabled: boolean): void {
  const queryClient = useQueryClient()
  const qcRef = useRef(queryClient)
  const queryKeyRef = useRef(queryKey)
  useEffect(() => {
    qcRef.current = queryClient
    queryKeyRef.current = queryKey
  }, [queryClient, queryKey])

  useReconnectingWebSocket(Boolean(pathPrefix) && enabled, {
    resolveWsUrl: async () => {
      if (!pathPrefix) return null
      const ticket = await fetchWsTicket(`${pathPrefix}/ws-ticket`)
      if (!ticket) return null
      return toWsUrl(API_BASE, `${pathPrefix}/ws?ticket=${encodeURIComponent(ticket)}`)
    },
    onMessage: (ev: MessageEvent) => {
      try {
        const raw = JSON.parse(String(ev.data)) as unknown
        if (isThreadPayload(raw) && raw.event === COMMENT_THREAD_UPDATED_EVENT) {
          void qcRef.current.invalidateQueries({ queryKey: queryKeyRef.current })
        }
      } catch {
        // пропускаем
      }
    },
  })
}

/** Realtime-обновление треда комментариев к задаче. */
export function useTaskCommentsThreadWebSocket(taskId: string | null | undefined): void {
  const id = taskId?.trim() || null
  const pathPrefix = id ? `/portal/tasks/${encodeURIComponent(id)}/comments` : null
  const qk: QueryKey = id ? taskCommentsQueryKey(id) : ['portal', 'task', 'comments', 'off']
  useCommentThreadResourceWebSocket(pathPrefix, qk, Boolean(id))
}

/** Realtime-обновление треда комментариев к документу. */
export function useDocumentCommentsThreadWebSocket(documentId: string | null | undefined): void {
  const id = documentId?.trim() || null
  const pathPrefix = id ? `/portal/documents/${encodeURIComponent(id)}/comments` : null
  const qk: QueryKey = id
    ? documentCommentsQueryKey(id)
    : (['portal', 'document', 'comments', 'off'] as const)
  useCommentThreadResourceWebSocket(pathPrefix, qk, Boolean(id))
}
