import { useMemo, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { listChats, listMessages } from '../api/chat/chatApi'
import {
  PORTAL_CHATS_ALL_QUERY_KEY,
  portalChatMessagesQueryKey,
  portalUsersQueryOptions,
} from '../api/queryKeys'
import { portalUsersAvatarBySub } from '../utils/avatar/portalUsersAvatarBySub'
import { playDirectMessageNotificationSound } from '../utils/notifications/notificationSound'
import { getUserDisplayLabel } from '../utils/userLabel'
import type { Chat, ChatMessage, UserPresence } from '../types/chat'

/** Редкий safety-net, если WS инбокса не доставил событие. */
const DM_SAFETY_REFETCH_MS = 8 * 60_000

export function useDmWidgetData(
  currentUserSub: string | null,
  open: boolean,
  activeChatId: string | null,
  viewIsChat: boolean,
  pickerSearch: string,
) {
  const { data: allChats = [], isError: isChatsError } = useQuery({
    queryKey: PORTAL_CHATS_ALL_QUERY_KEY,
    queryFn: () => listChats({ limit: 500 }),
    enabled: Boolean(currentUserSub),
    refetchInterval: DM_SAFETY_REFETCH_MS,
    refetchOnWindowFocus: true,
  })

  const sortedChats = useMemo(
    () =>
      [...(allChats as Chat[])].sort(
        (a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime(),
      ),
    [allChats],
  )

  const totalUnread = useMemo(
    () => sortedChats.reduce((sum: number, c: Chat) => sum + (c.unread_count ?? 0), 0),
    [sortedChats],
  )

  useEffect(() => {
    function handleDmEvent(e: Event) {
      const detail = (
        e as CustomEvent<{
          chat_id: string
          kind?: 'dm' | 'group'
          recipient_mentioned?: boolean
        }>
      ).detail
      void playDirectMessageNotificationSound(detail.chat_id, {
        bypassPerChatMute: detail.recipient_mentioned === true ? true : undefined,
      })
    }
    window.addEventListener('portal:dm_inbox_update', handleDmEvent)
    return () => window.removeEventListener('portal:dm_inbox_update', handleDmEvent)
  }, [])

  const refetchUsersWhileOpen = open && Boolean(currentUserSub)

  // Без refetchInterval — те же триггеры, что на странице чатов (heartbeat, фокус).
  const { data: portalUsers = [], isError: isUsersError } = useQuery({
    ...portalUsersQueryOptions(),
    enabled: refetchUsersWhileOpen,
  })

  const userMap: Record<string, string> = useMemo(
    () =>
      Object.fromEntries(
        portalUsers.map((u) => [u.sub, getUserDisplayLabel(u)]),
      ),
    [portalUsers],
  )

  const userAvatarBySub = useMemo(() => portalUsersAvatarBySub(portalUsers), [portalUsers])

  const presenceBySub = useMemo(() => {
    const m: Record<string, UserPresence> = {}
    for (const u of portalUsers) {
      m[u.sub] = u.presence ?? 'offline'
    }
    return m
  }, [portalUsers])

  const lastSeenBySub = useMemo(() => {
    const m: Record<string, string | null> = {}
    for (const u of portalUsers) {
      m[u.sub] = u.last_seen_at ?? null
    }
    return m
  }, [portalUsers])

  const avatarFocalBySub = useMemo(() => {
    const m: Record<string, { x: number; y: number } | undefined> = {}
    for (const u of portalUsers) {
      m[u.sub] =
        u.avatar_focal_x != null && u.avatar_focal_y != null
          ? { x: u.avatar_focal_x, y: u.avatar_focal_y }
          : undefined
    }
    return m
  }, [portalUsers])

  const filteredUsers = useMemo(() => {
    const q = pickerSearch.trim().toLowerCase()
    return portalUsers.filter(
      (u) =>
        u.sub !== currentUserSub &&
        (!q ||
          (u.display_name ?? '').toLowerCase().includes(q) ||
          (u.email ?? '').toLowerCase().includes(q) ||
          (u.username ?? '').toLowerCase().includes(q)),
    )
  }, [portalUsers, currentUserSub, pickerSearch])

  const { data: messages = [], isError: isMessagesError } = useQuery({
    queryKey: portalChatMessagesQueryKey(activeChatId!),
    queryFn: () => listMessages(activeChatId!),
    enabled: Boolean(activeChatId) && viewIsChat,
    select: (rows) =>
      (rows as ChatMessage[]).filter((m) => m.deleted_for_all_at == null),
  })

  return {
    sortedChats,
    totalUnread,
    portalUsers: portalUsers,
    userMap,
    userAvatarBySub,
    presenceBySub,
    lastSeenBySub,
    avatarFocalBySub,
    filteredUsers,
    messages,
    isChatsError,
    isUsersError,
    isMessagesError,
  }
}
