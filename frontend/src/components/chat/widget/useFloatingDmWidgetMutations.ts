import { useMutation, useQueryClient } from '@tanstack/react-query'

import { PORTAL_CHATS_ALL_QUERY_KEY, portalChatMessagesQueryKey } from '../../../api/queryKeys'
import {
  createChat,
  getOrCreateDirectChat,
  markChatRead,
} from '../../../api/chat/chatApi'
import {
  useDeleteChatMutation,
  useSendChatMessageMutation,
} from '../../../hooks/useChatMutations'
import { useNotifyToast } from '../../../hooks/useNotifyToast'
import { userFacingMessageFromUnknown } from '../../../utils/apiUserMessage'
import type { Chat } from '../../../types/chat'
import { patchPortalChatUnreadZero } from '../../../utils/chat/patchPortalChatsUnread'

type View = 'list' | 'picker' | 'groupPicker' | 'chat'

type Args = {
  currentUserSub: string | null
  activeChatId: string | null
  groupTitle: string
  groupSelected: Record<string, boolean>
  clearReply: () => void
  setGroupSettingsOpen: (open: boolean) => void
  setActiveChatId: (id: string | null) => void
  setView: (view: View) => void
  setMinimized: (minimized: boolean) => void
  setGroupTitle: (title: string) => void
  setGroupSelected: (sel: Record<string, boolean>) => void
  setPickerSearch: (s: string) => void
  setDeleteConfirmChat: (chat: Chat | null) => void
}

/**
 * Мутации плавающего DM-виджета: удаление чата, открытие/создание ЛС и группы,
 * отправка сообщения. Каждая мутация сама инвалидирует нужные react-query-ключи
 * и приводит состояние виджета в согласие (activeChatId/view/...).
 */
export function useFloatingDmWidgetMutations({
  currentUserSub,
  activeChatId,
  groupTitle,
  groupSelected,
  clearReply,
  setGroupSettingsOpen,
  setActiveChatId,
  setView,
  setMinimized,
  setGroupTitle,
  setGroupSelected,
  setPickerSearch,
  setDeleteConfirmChat,
}: Args) {
  const qc = useQueryClient()
  const notifyToast = useNotifyToast()

  const deleteChatMutation = useDeleteChatMutation(qc, (chatId) => {
    if (activeChatId === chatId) {
      setActiveChatId(null)
      clearReply()
      setGroupSettingsOpen(false)
      setView('list')
    }
    setDeleteConfirmChat(null)
  }, (message) => notifyToast(message, { silent: true }))

  const sendMutation = useSendChatMessageMutation({
    currentUserSub,
    messagesQueryKey: portalChatMessagesQueryKey,
    onErrorToast: notifyToast,
  })

  const openDmMutation = useMutation({
    mutationFn: (otherSub: string) => getOrCreateDirectChat(otherSub),
    onSuccess: (chat) => {
      void qc.invalidateQueries({ queryKey: PORTAL_CHATS_ALL_QUERY_KEY })
      clearReply()
      setGroupSettingsOpen(false)
      setActiveChatId(chat.id)
      setView('chat')
      setMinimized(false)
      void markChatRead(chat.id).then(() => patchPortalChatUnreadZero(qc, chat.id))
    },
    onError: (e: unknown) => notifyToast(userFacingMessageFromUnknown(e)),
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
      setPickerSearch('')
      clearReply()
      setActiveChatId(chat.id)
      setView('chat')
      setMinimized(false)
      void markChatRead(chat.id).then(() => patchPortalChatUnreadZero(qc, chat.id))
    },
    onError: (e: unknown) => notifyToast(userFacingMessageFromUnknown(e)),
  })

  return { deleteChatMutation, sendMutation, openDmMutation, createGroupMutation }
}
