import { useEffect, useRef } from 'react'
import { PORTAL_CHATS_ALL_QUERY_KEY, PORTAL_NOTIFICATIONS_ROOT_QUERY_KEY, PORTAL_USERS_QUERY_KEY } from '../api/queryKeys'

import { useQueryClient } from '@tanstack/react-query'

import { API_BASE } from '../api/rawClient'
import type { PortalUserShort, UserPresence } from '../api/usersApi'
import { useAuthStore } from '../store/authStore'
import {
  DM_INBOX_UPDATE_EVENT,
  DM_INBOX_WITHDRAWN_EVENT,
  PORTAL_NOTIFICATION_UPDATE_EVENT,
  PORTAL_NOTIFICATION_WITHDRAWN_EVENT,
  portalNotificationEventPlaysSound,
} from '../utils/notifications/inboxWithdraw'
import { fetchWsTicket } from './ws/fetchWsTicket'
import { toWsUrl } from './ws/url'
import { useReconnectingWebSocket } from './ws/useReconnectingWebSocket'

const DM_EVENT = DM_INBOX_UPDATE_EVENT
const DM_WITHDRAWN_EVENT = DM_INBOX_WITHDRAWN_EVENT
const NOTIF_EVENT = PORTAL_NOTIFICATION_UPDATE_EVENT
const NOTIF_WITHDRAWN_EVENT = PORTAL_NOTIFICATION_WITHDRAWN_EVENT
const PRESENCE_EVENT = 'presence_update'

type InboxKind = 'dm' | 'group'

type InboxDmPayload = {
  event: typeof DM_EVENT
  chat_id: string
  kind: InboxKind
  author_sub?: string
  preview_text?: string
  is_direct?: boolean
  chat_title?: string | null
  recipient_mentioned?: boolean
}

type PresenceUpdatePayload = {
  event: typeof PRESENCE_EVENT
  sub: string
  status: UserPresence
  last_seen_at?: string
}

type InboxPayload =
  | InboxDmPayload
  | { event: typeof NOTIF_EVENT }
  | { event: typeof NOTIF_WITHDRAWN_EVENT }
  | { event: typeof DM_WITHDRAWN_EVENT; chat_id: string }
  | PresenceUpdatePayload

function parseInboxPayload(raw: unknown): InboxPayload | null {
  if (raw === null || typeof raw !== 'object') return null
  const o = raw as Record<string, unknown>
  if (o.event === DM_EVENT && typeof o.chat_id === 'string') {
    const kind: InboxKind = o.kind === 'group' ? 'group' : 'dm'
    const dm: InboxDmPayload = { event: DM_EVENT, chat_id: o.chat_id, kind }
    if (typeof o.author_sub === 'string') {
      dm.author_sub = o.author_sub
    }
    if (typeof o.preview_text === 'string') {
      dm.preview_text = o.preview_text
    }
    if (typeof o.is_direct === 'boolean') {
      dm.is_direct = o.is_direct
    }
    if (typeof o.chat_title === 'string') {
      dm.chat_title = o.chat_title
    } else if (o.chat_title === null) {
      dm.chat_title = null
    }
    if (o.recipient_mentioned === true) {
      dm.recipient_mentioned = true
    }
    return dm
  }
  if (o.event === DM_WITHDRAWN_EVENT && typeof o.chat_id === 'string') {
    return { event: DM_WITHDRAWN_EVENT, chat_id: o.chat_id }
  }
  if (o.event === NOTIF_EVENT) {
    return { event: NOTIF_EVENT }
  }
  if (o.event === NOTIF_WITHDRAWN_EVENT) {
    return { event: NOTIF_WITHDRAWN_EVENT }
  }
  if (
    o.event === PRESENCE_EVENT &&
    typeof o.sub === 'string' &&
    (o.status === 'online' || o.status === 'away' || o.status === 'offline')
  ) {
    const presence: PresenceUpdatePayload = { event: PRESENCE_EVENT, sub: o.sub, status: o.status }
    if (typeof o.last_seen_at === 'string' && o.last_seen_at.length > 0) {
      presence.last_seen_at = o.last_seen_at
    }
    return presence
  }
  return null
}

/**
 * Одно соединение: события инбокса (DM-счётчики, портальные уведомления @).
 * Refetch кэша вместо поллинга; при сбое тикета/WS — повтор с backoff.
 */
export function usePortalInboxWebSocket(): void {
  const accessToken = useAuthStore((s) => s.accessToken)
  const userSub = useAuthStore((s) => s.user?.sub)
  const qc = useQueryClient()
  const qcRef = useRef(qc)
  useEffect(() => {
    qcRef.current = qc
  }, [qc])

  useReconnectingWebSocket(Boolean(accessToken) && Boolean(userSub), {
    resolveWsUrl: async () => {
      const ticket = await fetchWsTicket('/portal/inbox/ws-ticket')
      if (!ticket) return null
      return toWsUrl(API_BASE, `/portal/inbox/ws?ticket=${encodeURIComponent(ticket)}`)
    },
    onMessage: (event: MessageEvent) => {
      try {
        const raw = JSON.parse(event.data as string) as unknown
        const p = parseInboxPayload(raw)
        if (!p) return
        if (p.event === DM_EVENT) {
          void qcRef.current.refetchQueries({ queryKey: PORTAL_CHATS_ALL_QUERY_KEY })
          window.dispatchEvent(
            new CustomEvent('portal:dm_inbox_update', {
              detail: {
                chat_id: p.chat_id,
                kind: p.kind,
                author_sub: p.author_sub,
                preview_text: p.preview_text,
                is_direct: p.is_direct,
                chat_title: p.chat_title,
                recipient_mentioned: p.recipient_mentioned,
              },
            }),
          )
          return
        }
        if (p.event === NOTIF_EVENT || p.event === NOTIF_WITHDRAWN_EVENT) {
          void qcRef.current.refetchQueries({ queryKey: PORTAL_NOTIFICATIONS_ROOT_QUERY_KEY })
          if (portalNotificationEventPlaysSound(p.event)) {
            window.dispatchEvent(new CustomEvent('portal:notification_update'))
          }
          return
        }
        if (p.event === DM_WITHDRAWN_EVENT) {
          window.dispatchEvent(
            new CustomEvent('portal:dm_inbox_withdrawn', { detail: { chat_id: p.chat_id } }),
          )
          return
        }
        if (p.event === PRESENCE_EVENT) {
          const { sub, status, last_seen_at: lastSeenAt } = p
          qcRef.current.setQueryData<PortalUserShort[]>(PORTAL_USERS_QUERY_KEY, (prev) =>
            prev?.map((u) =>
              u.sub === sub
                ? { ...u, presence: status, ...(lastSeenAt ? { last_seen_at: lastSeenAt } : {}) }
                : u,
            ),
          )
        }
      } catch {
        // пропускаем
      }
    },
  })
}
