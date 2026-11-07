import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useSearchParams } from 'react-router'
import { PORTAL_CHATS_ALL_QUERY_KEY, portalChatMessagesQueryKey } from '../../api/queryKeys'
import {
  useDeleteChatMutation,
  useInvalidateChatQueries,
  useSendChatMessageMutation,
} from '../../hooks/useChatMutations'
import {
  createChat,
  getOrCreateDirectChat,
} from '../../api/chat/chatApi'
import { useAuthStore } from '../../store/authStore'
import { useNotifyToast } from '../../hooks/useNotifyToast'
import { userFacingMessageFromUnknown } from '../../utils/apiUserMessage'
import type { Chat, ChatMessage } from '../../types/chat'
import { chatDisplayName } from '@/utils/chat/chatDisplay'
import { dmPeerSub } from '@/utils/chat/dmPeerSub'
import {
  getDmChatNotificationSoundEnabled,
  setDmChatNotificationSoundEnabled,
} from '@/utils/chat/dmChatNotificationSoundSettings'
import { CHAT_ID_FROM_URL_RE } from './chatsConstants'
import { portalChatMessagesPageQueryKey } from './chatsQueryKeys'
import { shouldClearActiveChatOnBackToList, isChatsNarrowViewport, type ChatsLeftView } from './chatsPageLayout'
import { markChatReadAndPatchUnread } from './markChatReadAndPatchUnread'
import { useChatsPageDataQueries } from './useChatsPageDataQueries'
import { useChatsPageMessagesWebSocket } from './useChatsPageMessagesWebSocket'
import { useChatActivityRead } from '../../hooks/useChatActivityRead'
import { useChatsPortalUsersSlice } from './useChatsPortalUsersSlice'
import { createReplyStateHandlers } from '@/utils/chat/replyPreview'

export type { ChatsLeftView } from './chatsPageLayout'

export function useChatsPageController() {
  const currentUserSub = useAuthStore((s) => s.user?.sub ?? null)
  const qc = useQueryClient()
  const notifyToast = useNotifyToast()
  const [searchParams, setSearchParams] = useSearchParams()
  const [leftView, setLeftView] = useState<ChatsLeftView>('list')
  const [activeChatId, setActiveChatId] = useState<string | null>(null)
  const [pickerSearch, setPickerSearch] = useState('')
  const [dmNotifTick, setDmNotifTick] = useState(0)
  const [groupTitle, setGroupTitle] = useState('')
  const [groupSelected, setGroupSelected] = useState<Record<string, boolean>>({})
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [replyTo, setReplyTo] = useState<ChatMessage | null>(null)
  const [replyQuoteText, setReplyQuoteText] = useState<string | null>(null)
  const [chatCtxMenu, setChatCtxMenu] = useState<{ x: number; y: number; chat: Chat } | null>(null)
  const [deleteConfirmChat, setDeleteConfirmChat] = useState<Chat | null>(null)
  const [wsDeleteExitRowId, setWsDeleteExitRowId] = useState<string | null>(null)
  const wsDeleteExitTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const { handleReply, clearReply } = useMemo(
    () => createReplyStateHandlers(setReplyTo, setReplyQuoteText),
    [],
  )

  useEffect(() => {
    const raw = searchParams.get('chat')
    if (!raw || !CHAT_ID_FROM_URL_RE.test(raw)) return
    const t = window.setTimeout(() => setActiveChatId(raw), 0)
    return () => window.clearTimeout(t)
  }, [searchParams])

  const messageFromUrl = searchParams.get('message')
  const deepLinkMessageId =
    messageFromUrl && CHAT_ID_FROM_URL_RE.test(messageFromUrl) ? messageFromUrl : null

  const stripMessageFromUrl = useCallback(() => {
    setSearchParams(
      (prev) => {
        if (!prev.get('message')) return prev
        const next = new URLSearchParams(prev)
        next.delete('message')
        return next
      },
      { replace: true },
    )
  }, [setSearchParams])

  const buildPortalMessagesQueryKey = useCallback(
    (chatId: string) =>
      portalChatMessagesPageQueryKey(chatId, deepLinkMessageId ? 'wide' : 'default'),
    [deepLinkMessageId],
  )

  const {
    sortedChats,
    portalUsers,
    messages,
    chatsQueryError,
    usersQueryError,
    messagesQueryError,
  } = useChatsPageDataQueries({
    currentUserSub,
    activeChatId,
    deepLinkMessageId,
    buildPortalMessagesQueryKey,
  })

  const {
    userMap,
    userAvatarBySub,
    presenceBySub,
    lastSeenBySub,
    avatarFocalBySub,
    filteredUsers,
  } = useChatsPortalUsersSlice(portalUsers, currentUserSub, pickerSearch)

  const activeChat = sortedChats.find((c) => c.id === activeChatId)

  const invalidateChatQueries = useInvalidateChatQueries(qc, activeChatId)

  const deleteChatMutation = useDeleteChatMutation(qc, (chatId) => {
    if (activeChatId === chatId) {
      setActiveChatId(null)
      clearReply()
      setSettingsOpen(false)
    }
    setDeleteConfirmChat(null)
  }, (message) => notifyToast(message, { silent: true }))

  useEffect(() => {
    if (!activeChatId) return
    if (sortedChats.some((c) => c.id === activeChatId)) return
    const t = window.setTimeout(() => {
      setActiveChatId(null)
      clearReply()
      setSettingsOpen(false)
    }, 0)
    return () => window.clearTimeout(t)
  }, [activeChatId, sortedChats, clearReply])

  const onChatDeletedReset = useCallback(() => {
    setActiveChatId(null)
    clearReply()
    setSettingsOpen(false)
  }, [clearReply])

  const onWsMessageDeleting = useCallback((messageId: string) => {
    if (wsDeleteExitTimerRef.current) clearTimeout(wsDeleteExitTimerRef.current)
    setWsDeleteExitRowId(messageId)
    wsDeleteExitTimerRef.current = setTimeout(() => {
      setWsDeleteExitRowId(null)
    }, 360)
  }, [])

  const { ephemeralPeers, notifyEphemeral, emojiPong } = useChatsPageMessagesWebSocket({
    activeChatId,
    buildPortalMessagesQueryKey,
    currentUserSub,
    isDirect: Boolean(activeChat?.is_direct),
    invalidateChatQueries,
    onChatDeletedReset,
    onWsMessageDeleting,
  })

  const sendMutation = useSendChatMessageMutation({
    currentUserSub,
    messagesQueryKey: buildPortalMessagesQueryKey,
    onErrorToast: notifyToast,
  })

  const openDmMutation = useMutation({
    mutationFn: (otherSub: string) => getOrCreateDirectChat(otherSub),
    onSuccess: (chat) => {
      void qc.invalidateQueries({ queryKey: PORTAL_CHATS_ALL_QUERY_KEY })
      clearReply()
      setActiveChatId(chat.id)
      setLeftView('list')
      markChatReadAndPatchUnread(qc, chat.id)
    },
  })

  const createGroupMutation = useMutation({
    mutationFn: () => {
      const subs = Object.keys(groupSelected).filter((k) => groupSelected[k])
      return createChat({ title: groupTitle.trim(), member_subs: subs })
    },
    onSuccess: (chat) => {
      void qc.invalidateQueries({ queryKey: PORTAL_CHATS_ALL_QUERY_KEY })
      setGroupTitle('')
      setGroupSelected({})
      setLeftView('list')
      clearReply()
      setActiveChatId(chat.id)
      markChatReadAndPatchUnread(qc, chat.id)
    },
  })

  const dmError = openDmMutation.isError
    ? 'Не удалось открыть диалог. Попробуйте ещё раз.'
    : null

  const groupError = createGroupMutation.isError
    ? 'Не удалось создать группу. Проверьте название и участников.'
    : null

  const chatsListError = chatsQueryError
    ? userFacingMessageFromUnknown(chatsQueryError)
    : null
  const usersListError = usersQueryError
    ? userFacingMessageFromUnknown(usersQueryError)
    : null
  const messagesListError = messagesQueryError
    ? userFacingMessageFromUnknown(messagesQueryError)
    : null

  const openChat = useCallback(
    (chatId: string) => {
      clearReply()
      setActiveChatId(chatId)
      markChatReadAndPatchUnread(qc, chatId)
    },
    [qc, clearReply],
  )

  const onChatActivity = useChatActivityRead(activeChatId, activeChat?.unread_count ?? 0)

  const activeTitle = activeChat
    ? chatDisplayName(activeChat, currentUserSub, userMap)
    : null

  const activeDmPeerSub =
    activeChat?.is_direct && currentUserSub ? dmPeerSub(activeChat, currentUserSub) : null

  const mentionCandidatesForActiveChat = useMemo(() => {
    if (!activeChat || !currentUserSub) return []
    const subs = activeChat.member_subs.filter((s) => s !== currentUserSub)
    return portalUsers.filter((u) => subs.includes(u.sub))
  }, [activeChat, currentUserSub, portalUsers])

  const handleDmSoundClick = useCallback((e: React.MouseEvent, chatId: string) => {
    e.stopPropagation()
    e.preventDefault()
    const next = !getDmChatNotificationSoundEnabled(chatId)
    setDmChatNotificationSoundEnabled(chatId, next)
    setDmNotifTick((n) => n + 1)
  }, [])

  const openSettings = useCallback(() => {
    if (!activeChat || activeChat.is_direct) return
    setSettingsOpen(true)
  }, [activeChat])

  const canSubmitGroup =
    groupTitle.trim().length > 0 && Object.values(groupSelected).some(Boolean)

  const sidebarTitle =
    leftView === 'list' ? 'Все чаты' : leftView === 'picker' ? 'Новый диалог' : 'Новая группа'

  const backToList = useCallback(() => {
    if (shouldClearActiveChatOnBackToList(leftView, isChatsNarrowViewport(window.innerWidth))) {
      setActiveChatId(null)
      clearReply()
      setSettingsOpen(false)
      setSearchParams(
        (prev) => {
          if (!prev.get('chat')) return prev
          const next = new URLSearchParams(prev)
          next.delete('chat')
          return next
        },
        { replace: true },
      )
    }
    setLeftView('list')
    setPickerSearch('')
    setGroupTitle('')
    setGroupSelected({})
  }, [leftView, setSearchParams, clearReply])

  const startNewDm = useCallback(() => {
    setPickerSearch('')
    setLeftView('picker')
  }, [])

  const startNewGroup = useCallback(() => {
    setPickerSearch('')
    setGroupTitle('')
    setGroupSelected({})
    setLeftView('groupPicker')
  }, [])

  const onAfterForward = useCallback(
    (targetId: string) => {
      clearReply()
      setActiveChatId(targetId)
      markChatReadAndPatchUnread(qc, targetId)
      void qc.invalidateQueries({ queryKey: portalChatMessagesQueryKey(targetId) })
    },
    [qc, clearReply],
  )

  return {
    qc,
    currentUserSub,
    portalUsers: portalUsers,
    leftView,
    setLeftView,
    activeChatId,
    setActiveChatId,
    pickerSearch,
    setPickerSearch,
    dmNotifTick,
    groupTitle,
    setGroupTitle,
    groupSelected,
    setGroupSelected,
    settingsOpen,
    setSettingsOpen,
    replyTo,
    clearReply,
    replyQuoteText,
    handleReply,
    chatCtxMenu,
    setChatCtxMenu,
    deleteConfirmChat,
    setDeleteConfirmChat,
    wsDeleteExitRowId,
    deepLinkMessageId,
    stripMessageFromUrl,
    buildPortalMessagesQueryKey,
    sortedChats,
    userMap,
    userAvatarBySub,
    presenceBySub,
    lastSeenBySub,
    avatarFocalBySub,
    filteredUsers,
    activeChat,
    messages,
    chatsListError,
    usersListError,
    messagesListError,
    deleteChatMutation,
    sendMutation,
    openDmMutation,
    createGroupMutation,
    dmError,
    groupError,
    openChat,
    onChatActivity,
    activeTitle,
    activeDmPeerSub,
    mentionCandidatesForActiveChat,
    handleDmSoundClick,
    openSettings,
    canSubmitGroup,
    sidebarTitle,
    backToList,
    startNewDm,
    startNewGroup,
    onAfterForward,
    ephemeralPeers,
    notifyEphemeral,
    emojiPong,
  }
}
