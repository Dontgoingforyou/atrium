import { useMemo } from 'react'
import { keepPreviousData, useQuery } from '@tanstack/react-query'

import { listChats, listMessages } from '../../api/chat/chatApi'
import { PORTAL_CHATS_ALL_QUERY_KEY, portalUsersQueryOptions } from '../../api/queryKeys'
import type { ChatMessage } from '../../types/chat'
import { CHATS_DM_SAFETY_REFETCH_MS } from './chatsConstants'
import { PORTAL_MESSAGES_IDLE_QUERY_KEY, type BuildPortalMessagesPageQueryKey } from './chatsQueryKeys'

type Args = {
  currentUserSub: string | null
  activeChatId: string | null
  deepLinkMessageId: string | null
  buildPortalMessagesQueryKey: BuildPortalMessagesPageQueryKey
}

export function useChatsPageDataQueries({
  currentUserSub,
  activeChatId,
  deepLinkMessageId,
  buildPortalMessagesQueryKey,
}: Args) {
  const {
    data: allChats = [],
    isError: chatsIsError,
    error: chatsError,
  } = useQuery({
    queryKey: PORTAL_CHATS_ALL_QUERY_KEY,
    queryFn: () => listChats({ limit: 500 }),
    enabled: Boolean(currentUserSub),
    refetchInterval: CHATS_DM_SAFETY_REFETCH_MS,
    refetchOnWindowFocus: true,
  })

  const sortedChats = useMemo(() => {
    return [...allChats].sort(
      (a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime(),
    )
  }, [allChats])

  const {
    data: portalUsers = [],
    isError: usersIsError,
    error: usersError,
  } = useQuery({
    ...portalUsersQueryOptions(),
    placeholderData: keepPreviousData,
    enabled: Boolean(currentUserSub),
  })

  const {
    data: messages = [],
    isError: messagesIsError,
    error: messagesError,
  } = useQuery({
    queryKey: activeChatId
      ? buildPortalMessagesQueryKey(activeChatId)
      : PORTAL_MESSAGES_IDLE_QUERY_KEY,
    queryFn: () =>
      listMessages(
        activeChatId!,
        deepLinkMessageId
          ? { limit: 500, aroundMessageId: deepLinkMessageId }
          : undefined,
      ),
    enabled: Boolean(activeChatId),
  })

  return {
    sortedChats,
    portalUsers,
    messages: messages as ChatMessage[],
    chatsQueryError: chatsIsError ? chatsError : null,
    usersQueryError: usersIsError ? usersError : null,
    messagesQueryError: messagesIsError ? messagesError : null,
  }
}
