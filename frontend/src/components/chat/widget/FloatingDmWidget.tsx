import { useEffect, useMemo, useState } from 'react'

import { setPortalActiveChatOnFloatingWidget } from '@/utils/chat/portalActiveChatStorage'
import { useLocation } from 'react-router'
import { useQueryClient } from '@tanstack/react-query'
import { useInvalidateChatQueries } from '../../../hooks/useChatMutations'

import { markChatRead } from '../../../api/chat/chatApi'
import { useAuthStore } from '../../../store/authStore'
import type { Chat, ChatMessage } from '../../../types/chat'
import { useDmWidgetData } from '../../../hooks/useDmWidgetData'
import { FloatingDmWidgetOverlays } from './FloatingDmWidgetOverlays'
import {
  getDmChatNotificationSoundEnabled,
  setDmChatNotificationSoundEnabled,
} from '@/utils/chat/dmChatNotificationSoundSettings'
import { createReplyStateHandlers } from '@/utils/chat/replyPreview'
import { chatDisplayName } from '@/utils/chat/chatDisplay'
import { patchPortalChatUnreadZero } from '../../../utils/chat/patchPortalChatsUnread'
import { dmPeerSub } from '@/utils/chat/dmPeerSub'
import {
  readFloatingDmWidgetSession,
  writeFloatingDmWidgetSession,
  type FloatingDmWidgetView,
} from '@/utils/chat/floatingDmWidgetSession'
import { FloatingDmWidgetPanel } from './FloatingDmWidgetPanel'
import { FloatingDmWidgetToggle } from './FloatingDmWidgetToggle'
import { useFloatingDmWidgetRealtime } from './useFloatingDmWidgetRealtime'
import { useFloatingDmWidgetMutations } from './useFloatingDmWidgetMutations'
import chromeStyles from '@/styles/modules/chat/FloatingDmWidgetChrome.module.css'

type View = FloatingDmWidgetView

export function FloatingDmWidget() {
  const location = useLocation()
  const [panelMounted, setPanelMounted] = useState(false)
  const [minimized, setMinimized] = useState(false)
  const [view, setView] = useState<View>('list')
  const [activeChatId, setActiveChatId] = useState<string | null>(null)
  const [pickerSearch, setPickerSearch] = useState('')
  const [groupTitle, setGroupTitle] = useState('')
  const [groupSelected, setGroupSelected] = useState<Record<string, boolean>>({})
  const currentUserSub = useAuthStore((s) => s.user?.sub ?? null)
  const qc = useQueryClient()
  const [dmNotifTick, setDmNotifTick] = useState(0)
  const [replyTo, setReplyTo] = useState<ChatMessage | null>(null)
  const [replyQuoteText, setReplyQuoteText] = useState<string | null>(null)
  const [groupSettingsOpen, setGroupSettingsOpen] = useState(false)
  const [chatCtxMenu, setChatCtxMenu] = useState<{ x: number; y: number; chat: Chat } | null>(null)
  const [deleteConfirmChat, setDeleteConfirmChat] = useState<Chat | null>(null)

  const { handleReply, clearReply } = useMemo(
    () => createReplyStateHandlers(setReplyTo, setReplyQuoteText),
    [],
  )

  const {
    sortedChats,
    totalUnread,
    portalUsers,
    userMap,
    userAvatarBySub,
    presenceBySub,
    lastSeenBySub,
    avatarFocalBySub,
    filteredUsers,
    messages,
  } = useDmWidgetData(currentUserSub, panelMounted, activeChatId, view === 'chat', pickerSearch)

  const invalidateChatQueries = useInvalidateChatQueries(qc, activeChatId)

  useEffect(() => {
    if (panelMounted && view === 'chat' && activeChatId) {
      setPortalActiveChatOnFloatingWidget(activeChatId)
    } else {
      setPortalActiveChatOnFloatingWidget(null)
    }
    return () => setPortalActiveChatOnFloatingWidget(null)
  }, [panelMounted, view, activeChatId])

  useEffect(() => {
    if (!panelMounted) return
    writeFloatingDmWidgetSession({ view, activeChatId })
  }, [panelMounted, view, activeChatId])

  useEffect(() => {
    if (!activeChatId) return
    if (sortedChats.some((c) => c.id === activeChatId)) return
    const t = window.setTimeout(() => {
      setActiveChatId(null)
      clearReply()
      setGroupSettingsOpen(false)
      setView('list')
    }, 0)
    return () => window.clearTimeout(t)
  }, [activeChatId, sortedChats, clearReply])

  const chatIdForWs = panelMounted && activeChatId ? activeChatId : null
  const chatIdForEphemeral = view === 'chat' && panelMounted ? activeChatId : null
  const activeChat = sortedChats.find((c: Chat) => c.id === activeChatId)

  const { emojiPong, ephemeralPeers, notifyEphemeral, onChatActivity } = useFloatingDmWidgetRealtime({
    chatIdForWs,
    chatIdForEphemeral,
    currentUserSub,
    activeChatId,
    view,
    panelMounted,
    minimized,
    activeChat,
    invalidateChatQueries,
    clearReply,
    setGroupSettingsOpen,
    setActiveChatId,
    setView,
  })

  const { deleteChatMutation, sendMutation, openDmMutation, createGroupMutation } =
    useFloatingDmWidgetMutations({
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
    })

  function goToList() {
    setView('list')
    setPickerSearch('')
    setGroupTitle('')
    setGroupSelected({})
  }

  function openChat(chatId: string) {
    clearReply()
    setGroupSettingsOpen(false)
    setActiveChatId(chatId)
    setView('chat')
    setMinimized(false)
    void markChatRead(chatId).then(() => patchPortalChatUnreadZero(qc, chatId))
  }

  function restoreSessionFromStorage() {
    const saved = readFloatingDmWidgetSession()
    if (saved) {
      setView(saved.view)
      setActiveChatId(saved.activeChatId)
    } else {
      setView('list')
      setActiveChatId(null)
      setPickerSearch('')
      setGroupTitle('')
      setGroupSelected({})
      clearReply()
      setGroupSettingsOpen(false)
    }
  }

  function handleToggle() {
    if (!panelMounted) {
      restoreSessionFromStorage()
      setPanelMounted(true)
      setMinimized(false)
      return
    }
    if (minimized) {
      setMinimized(false)
      return
    }
    setMinimized(true)
  }

  function handleMinimize() {
    setMinimized(true)
  }

  function handleClosePanel() {
    setPanelMounted(false)
    setMinimized(false)
    writeFloatingDmWidgetSession(null)
    setPortalActiveChatOnFloatingWidget(null)
  }

  function handleDmSoundClick(e: React.MouseEvent, chatId: string) {
    e.stopPropagation()
    e.preventDefault()
    const next = !getDmChatNotificationSoundEnabled(chatId)
    setDmChatNotificationSoundEnabled(chatId, next)
    setDmNotifTick((n) => n + 1)
  }

  const mentionCandidatesForActiveChat = useMemo(() => {
    if (!activeChat || !currentUserSub) return []
    const subs = activeChat.member_subs.filter((s) => s !== currentUserSub)
    return portalUsers.filter((u) => subs.includes(u.sub))
  }, [activeChat, currentUserSub, portalUsers])
  const activeChatName = activeChat ? chatDisplayName(activeChat, currentUserSub, userMap) : null
  const activeDmPeerSub =
    activeChat && currentUserSub ? dmPeerSub(activeChat, currentUserSub) : null
  const dmSoundEnabled = activeChatId ? getDmChatNotificationSoundEnabled(activeChatId) : false

  const headerTitle =
    view === 'list'
      ? 'Сообщения'
      : view === 'picker'
        ? 'Новый диалог'
        : view === 'groupPicker'
          ? 'Новая группа'
          : (activeChatName ?? 'Чат')

  const canSubmitGroup =
    groupTitle.trim().length > 0 && Object.values(groupSelected).some(Boolean)

  const minimizedBarLabel =
    view === 'chat' && activeChatName ? activeChatName : 'Сообщения'

  if (location.pathname.startsWith('/chats')) {
    return null
  }

  return (
    <>
      <FloatingDmWidgetToggle
        totalUnread={totalUnread}
        onClick={handleToggle}
        expanded={panelMounted && !minimized}
      />

      {panelMounted && minimized ? (
        <button
          type="button"
          className={chromeStyles.minimizedBar}
          onClick={() => setMinimized(false)}
          aria-label="Развернуть чат"
        >
          <span className={chromeStyles.minimizedBarTitle}>{minimizedBarLabel}</span>
          <span aria-hidden>▲</span>
        </button>
      ) : null}

      {panelMounted ? (
        <FloatingDmWidgetPanel
          view={view}
          setView={setView}
          panelHidden={minimized}
          onMinimize={handleMinimize}
          onClosePanel={handleClosePanel}
          activeChatId={activeChatId}
          activeChat={activeChat}
          activeChatName={activeChatName}
          activeDmPeerSub={activeDmPeerSub}
          userAvatarBySub={userAvatarBySub}
          avatarFocalBySub={avatarFocalBySub}
          presenceBySub={presenceBySub}
          lastSeenBySub={lastSeenBySub}
          dmSoundEnabled={dmSoundEnabled}
          headerTitle={headerTitle}
          sortedChats={sortedChats}
          currentUserSub={currentUserSub}
          userMap={userMap}
          dmNotifTick={dmNotifTick}
          pickerSearch={pickerSearch}
          setPickerSearch={setPickerSearch}
          groupTitle={groupTitle}
          setGroupTitle={setGroupTitle}
          groupSelected={groupSelected}
          setGroupSelected={setGroupSelected}
          filteredUsers={filteredUsers}
          mentionCandidatesForActiveChat={mentionCandidatesForActiveChat}
          messages={messages}
          replyTo={replyTo}
          clearReply={clearReply}
          replyQuoteText={replyQuoteText}
          onReply={handleReply}
          sendMutationPending={sendMutation.isPending}
          openDmMutationPending={openDmMutation.isPending}
          openDmMutationError={openDmMutation.isError}
          createGroupMutationPending={createGroupMutation.isPending}
          createGroupMutationError={createGroupMutation.isError}
          canSubmitGroup={canSubmitGroup}
          goToList={goToList}
          openChat={openChat}
          handleDmSoundClick={handleDmSoundClick}
          setGroupSettingsOpen={setGroupSettingsOpen}
          setChatCtxMenu={setChatCtxMenu}
          openDmMutationMutate={(sub) => openDmMutation.mutate(sub)}
          createGroupMutationMutate={() => createGroupMutation.mutate()}
          sendMutationMutateAsync={(args) => sendMutation.mutateAsync(args)}
          ephemeralPeers={ephemeralPeers}
          notifyEphemeral={notifyEphemeral}
          onAfterForward={(targetId) => {
            clearReply()
            setGroupSettingsOpen(false)
            setActiveChatId(targetId)
            setView('chat')
            setMinimized(false)
            void markChatRead(targetId).then(() => patchPortalChatUnreadZero(qc, targetId))
            void qc.invalidateQueries({ queryKey: ['portal', 'messages', targetId] })
          }}
          onChatActivity={onChatActivity}
          emojiPong={emojiPong}
        />
      ) : null}

      <FloatingDmWidgetOverlays
        groupSettingsOpen={groupSettingsOpen}
        activeChat={activeChat}
        currentUserSub={currentUserSub}
        portalUsers={portalUsers}
        userMap={userMap}
        presenceBySub={presenceBySub}
        onCloseGroupSettings={() => setGroupSettingsOpen(false)}
        onAfterSelfLeave={() => {
          setGroupSettingsOpen(false)
          clearReply()
          setActiveChatId(null)
          setView('list')
        }}
        chatCtxMenu={chatCtxMenu}
        onCloseCtxMenu={() => setChatCtxMenu(null)}
        onRequestDeleteFromCtx={(chat) => setDeleteConfirmChat(chat)}
        deleteConfirmChat={deleteConfirmChat}
        deleteChatMutation={deleteChatMutation}
        onCancelDelete={() => setDeleteConfirmChat(null)}
      />
    </>
  )
}
