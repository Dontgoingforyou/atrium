import { useQueryClient, type QueryKey } from '@tanstack/react-query'
import { useCallback, useEffect, useRef, useState } from 'react'

import { API_BASE } from '../api/rawClient'
import { PORTAL_NAVIGATION_TREE_QUERY_KEY } from '../api/queryKeys'
import type { PageViewer } from '../components/common/PageViewersBanner'
import { useAuthStore } from '../store/authStore'
import {
  documentChildrenQueryKey,
  portalDocumentQueryKey,
} from '../utils/documents/documentNavigation'
import { fetchWsTicket } from './ws/fetchWsTicket'
import { toWsUrl } from './ws/url'
import { useReconnectingWebSocket } from './ws/useReconnectingWebSocket'

const DOCUMENT_UPDATED_EVENT = 'document_updated'
const PAGE_VIEWERS_EVENT = 'page_viewers'

type WsPayload = { event: string; viewers?: PageViewer[] }

function isPayload(raw: unknown): raw is WsPayload {
  return (
    raw !== null && typeof raw === 'object' && 'event' in raw && typeof (raw as WsPayload).event === 'string'
  )
}

function parseViewers(raw: WsPayload): PageViewer[] {
  if (!Array.isArray(raw.viewers)) return []
  return raw.viewers.filter(
    (v): v is PageViewer =>
      Boolean(v) &&
      typeof v === 'object' &&
      typeof (v as PageViewer).sub === 'string' &&
      typeof (v as PageViewer).display_name === 'string',
  )
}

/**
 * Realtime: refetch по ``document_updated`` + roster ``page_viewers``.
 */
function useDocumentRealtimeResource(
  pathBase: string | null,
  queryKeys: QueryKey[],
  enabled: boolean,
  onViewers?: (viewers: PageViewer[]) => void,
): void {
  const accessToken = useAuthStore((s) => s.accessToken)
  const queryClient = useQueryClient()
  const qcRef = useRef(queryClient)
  const qksRef = useRef(queryKeys)
  const onViewersRef = useRef(onViewers)
  useEffect(() => {
    qcRef.current = queryClient
    qksRef.current = queryKeys
    onViewersRef.current = onViewers
  }, [queryClient, queryKeys, onViewers])

  useReconnectingWebSocket(Boolean(pathBase) && Boolean(accessToken) && enabled && queryKeys.length > 0, {
    resolveWsUrl: async () => {
      if (!pathBase) return null
      const ticket = await fetchWsTicket(`${pathBase}-ws-ticket`)
      if (!ticket) return null
      return toWsUrl(API_BASE, `${pathBase}-ws?ticket=${encodeURIComponent(ticket)}`)
    },
    onMessage: (ev: MessageEvent) => {
      try {
        const raw = JSON.parse(String(ev.data)) as unknown
        if (!isPayload(raw)) return
        if (raw.event === PAGE_VIEWERS_EVENT) {
          onViewersRef.current?.(parseViewers(raw))
          return
        }
        if (raw.event === DOCUMENT_UPDATED_EVENT) {
          for (const qk of qksRef.current) {
            void qcRef.current.invalidateQueries({ queryKey: qk })
          }
        }
      } catch {
        // пропускаем
      }
    },
  })
}

/**
 * Обновления открытого документа (тело) и дочерних списков + viewers.
 */
export function useOpenDocumentWebSocket(
  documentId: string | null | undefined,
  opts: { parentDocumentId: string | null | undefined },
): PageViewer[] {
  const [viewersState, setViewersState] = useState<{ forId: string | null; list: PageViewer[] }>({
    forId: null,
    list: [],
  })
  const id = documentId?.trim() || null
  const pathBase = id ? `/portal/documents/${encodeURIComponent(id)}/content` : null
  const parent = opts.parentDocumentId?.trim() || null
  const qks: QueryKey[] = []
  if (id) {
    qks.push(portalDocumentQueryKey(id))
    qks.push(documentChildrenQueryKey(id))
  }
  if (parent) {
    qks.push(documentChildrenQueryKey(parent))
  }

  const onViewers = useCallback(
    (next: PageViewer[]) => {
      setViewersState({ forId: id, list: next })
    },
    [id],
  )

  useDocumentRealtimeResource(pathBase, qks, Boolean(id), onViewers)
  return viewersState.forId === id ? viewersState.list : []
}

/**
 * Глобальная подписка: обновляет дерево навигации в реальном времени у всех пользователей.
 * Подключается один раз в AppLayout — работает на любой странице.
 */
export function useNavigationTreeWebSocket(): void {
  useDocumentRealtimeResource(
    '/portal/navigation-tree',
    [PORTAL_NAVIGATION_TREE_QUERY_KEY],
    true,
  )
}
