import { useCallback, useState } from 'react'

import { API_BASE } from '../api/rawClient'
import type { PageViewer } from '../components/common/PageViewersBanner'
import { useAuthStore } from '../store/authStore'
import { fetchWsTicket } from './ws/fetchWsTicket'
import { toWsUrl } from './ws/url'
import { useReconnectingWebSocket } from './ws/useReconnectingWebSocket'

const PAGE_VIEWERS_EVENT = 'page_viewers'

function parseViewers(raw: unknown): PageViewer[] {
  if (!raw || typeof raw !== 'object') return []
  const event = (raw as { event?: unknown }).event
  const viewers = (raw as { viewers?: unknown }).viewers
  if (event !== PAGE_VIEWERS_EVENT || !Array.isArray(viewers)) return []
  return viewers.filter(
    (v): v is PageViewer =>
      Boolean(v) &&
      typeof v === 'object' &&
      typeof (v as PageViewer).sub === 'string' &&
      typeof (v as PageViewer).display_name === 'string',
  )
}

export function useTaskPageViewers(taskId: string | null | undefined): PageViewer[] {
  const [viewersState, setViewersState] = useState<{ forId: string | null; list: PageViewer[] }>({
    forId: null,
    list: [],
  })
  const accessToken = useAuthStore((s) => s.accessToken)
  const id = taskId?.trim() || null

  const onViewers = useCallback(
    (next: PageViewer[]) => {
      setViewersState({ forId: id, list: next })
    },
    [id],
  )

  useReconnectingWebSocket(Boolean(id) && Boolean(accessToken), {
    resolveWsUrl: async () => {
      if (!id) return null
      const path = `/portal/tasks/${encodeURIComponent(id)}/page`
      const ticket = await fetchWsTicket(`${path}-ws-ticket`)
      if (!ticket) return null
      return toWsUrl(API_BASE, `${path}-ws?ticket=${encodeURIComponent(ticket)}`)
    },
    onMessage: (ev: MessageEvent) => {
      try {
        onViewers(parseViewers(JSON.parse(String(ev.data)) as unknown))
      } catch {
        // skip
      }
    },
  })

  return viewersState.forId === id ? viewersState.list : []
}
