import { useEffect } from 'react'

import { setPortalActiveChatOnChatsPage } from '@/utils/chat/portalActiveChatStorage'
import {
  GUIDED_TOUR_CLOSE_CTX_EVENT,
  GUIDED_TOUR_OPEN_CTX_EVENT,
  TOUR_DEMO_CHAT_TITLE,
  type GuidedTourOpenCtxDetail,
} from '../../onboarding/ensureTourDemoChat'
import { useChatsPageController } from './useChatsPageController'
import { ChatsSidebarHeader } from './ChatsSidebarHeader'
import { ChatsSidebarChatList } from './ChatsSidebarChatList'
import { ChatsSidebarDmPicker } from './ChatsSidebarDmPicker'
import { ChatsSidebarGroupForm } from './ChatsSidebarGroupForm'
import { ChatsThreadColumn } from './ChatsThreadColumn'
import { ChatsPageOverlays } from './ChatsPageOverlays'
import sidebar from '@/styles/modules/chat/ChatsPageSidebar.module.css'
import thread from '@/styles/modules/chat/ChatsPageThread.module.css'

export function ChatsPage() {
  const c = useChatsPageController()
  const { activeChatId, sortedChats, setChatCtxMenu } = c

  useEffect(() => {
    setPortalActiveChatOnChatsPage(activeChatId)
    return () => setPortalActiveChatOnChatsPage(null)
  }, [activeChatId])

  useEffect(() => {
    function onTourOpenCtx(ev: Event) {
      const detail = (ev as CustomEvent<GuidedTourOpenCtxDetail>).detail
      if (detail?.kind !== 'chat-row') return
      const demo =
        sortedChats.find((ch) => !ch.is_direct && ch.title === TOUR_DEMO_CHAT_TITLE) ??
        sortedChats[0]
      if (!demo) return
      const row = document.querySelector<HTMLElement>('[data-tour="chats-row"]')
      const r = row?.getBoundingClientRect()
      if (!r) return
      setChatCtxMenu({
        x: Math.min(r.left + 24, window.innerWidth - 200),
        y: Math.min(r.bottom - 8, window.innerHeight - 80),
        chat: demo,
      })
    }
    function onTourCloseCtx() {
      setChatCtxMenu(null)
    }
    document.addEventListener(GUIDED_TOUR_OPEN_CTX_EVENT, onTourOpenCtx)
    document.addEventListener(GUIDED_TOUR_CLOSE_CTX_EVENT, onTourCloseCtx)
    return () => {
      document.removeEventListener(GUIDED_TOUR_OPEN_CTX_EVENT, onTourOpenCtx)
      document.removeEventListener(GUIDED_TOUR_CLOSE_CTX_EVENT, onTourCloseCtx)
    }
  }, [sortedChats, setChatCtxMenu])

  const showThreadNarrow = c.leftView === 'list' && Boolean(c.activeChatId)

  return (
    <div className={sidebar.root}>
      <div className={sidebar.layout}>
        <div
          className={
            showThreadNarrow ? `${sidebar.sidebar} ${sidebar.sidebarNarrowHidden}` : sidebar.sidebar
          }
          data-tour="chats-sidebar"
        >
          <ChatsSidebarHeader
            leftView={c.leftView}
            sidebarTitle={c.sidebarTitle}
            onBackToList={c.backToList}
            onNewDm={c.startNewDm}
            onNewGroup={c.startNewGroup}
          />

          {c.leftView === 'list' && (
            <ChatsSidebarChatList
              sortedChats={c.sortedChats}
              listError={c.chatsListError}
              currentUserSub={c.currentUserSub}
              userMap={c.userMap}
              userAvatarBySub={c.userAvatarBySub}
              presenceBySub={c.presenceBySub}
              lastSeenBySub={c.lastSeenBySub}
              avatarFocalBySub={c.avatarFocalBySub}
              dmNotifTick={c.dmNotifTick}
              activeChatId={c.activeChatId}
              onChatOpen={c.openChat}
              onDmSoundClick={c.handleDmSoundClick}
              onChatRowContextMenu={(ev, chat) => {
                c.setChatCtxMenu({ x: ev.clientX, y: ev.clientY, chat })
              }}
            />
          )}

          {c.leftView === 'picker' && (
            <ChatsSidebarDmPicker
              pickerSearch={c.pickerSearch}
              onPickerSearchChange={c.setPickerSearch}
              filteredUsers={c.filteredUsers}
              userMap={c.userMap}
              dmError={c.dmError}
              usersError={c.usersListError}
              isPending={c.openDmMutation.isPending}
              onSelectUser={(sub) => c.openDmMutation.mutate(sub)}
            />
          )}

          {c.leftView === 'groupPicker' && (
            <ChatsSidebarGroupForm
              groupTitle={c.groupTitle}
              onGroupTitleChange={c.setGroupTitle}
              pickerSearch={c.pickerSearch}
              onPickerSearchChange={c.setPickerSearch}
              groupError={c.groupError}
              usersError={c.usersListError}
              filteredUsers={c.filteredUsers}
              userMap={c.userMap}
              groupSelected={c.groupSelected}
              onMemberToggle={(sub, checked) =>
                c.setGroupSelected((prev) => ({ ...prev, [sub]: checked }))
              }
              canSubmitGroup={c.canSubmitGroup}
              isPending={c.createGroupMutation.isPending}
              onSubmit={() => c.createGroupMutation.mutate()}
            />
          )}
        </div>

        <div
          className={
            showThreadNarrow ? thread.detail : `${thread.detail} ${thread.detailNarrowHidden}`
          }
          data-tour="chats-thread"
          onMouseMove={c.onChatActivity}
        >
          {c.activeChatId && c.activeTitle ? (
            <ChatsThreadColumn
              portalMessagesQueryKey={
                c.activeChatId ? c.buildPortalMessagesQueryKey(c.activeChatId) : undefined
              }
              activeChatId={c.activeChatId}
              activeTitle={c.activeTitle}
              activeChat={c.activeChat}
              activeDmPeerSub={c.activeDmPeerSub}
              mentionUsers={c.mentionCandidatesForActiveChat}
              messages={c.messages}
              messagesError={c.messagesListError}
              currentUserSub={c.currentUserSub}
              userMap={c.userMap}
              userAvatarBySub={c.userAvatarBySub}
              avatarFocalBySub={c.avatarFocalBySub}
              presenceBySub={c.presenceBySub}
              lastSeenBySub={c.lastSeenBySub}
              sortedChats={c.sortedChats}
              deepLinkMessageId={c.deepLinkMessageId}
              stripMessageFromUrl={c.stripMessageFromUrl}
              wsDeleteExitRowId={c.wsDeleteExitRowId}
              hideOpenChatsLink={true}
              onBackToList={() => c.setActiveChatId(null)}
              replyTo={c.replyTo}
              replyQuoteText={c.replyQuoteText}
              clearReply={c.clearReply}
              onReply={c.handleReply}
              sendMutation={c.sendMutation}
              onAfterForward={c.onAfterForward}
              handleDmSoundClick={c.handleDmSoundClick}
              openSettings={c.openSettings}
              ephemeralPeers={c.ephemeralPeers}
              notifyEphemeral={c.notifyEphemeral}
              emojiPong={c.emojiPong}
            />
          ) : (
            <div className={thread.detailPlaceholder}>
              Выберите чат слева или начните новый диалог / группу
            </div>
          )}
        </div>
      </div>

      <ChatsPageOverlays
        settingsOpen={c.settingsOpen}
        onCloseSettings={() => c.setSettingsOpen(false)}
        activeChat={c.activeChat}
        currentUserSub={c.currentUserSub}
        portalUsers={c.portalUsers}
        userMap={c.userMap}
        presenceBySub={c.presenceBySub}
        onAfterSelfLeaveSettings={() => {
          c.setSettingsOpen(false)
          c.clearReply()
          c.setActiveChatId(null)
        }}
        chatCtxMenu={c.chatCtxMenu}
        onDismissCtxMenu={() => c.setChatCtxMenu(null)}
        onPickDeleteFromCtxMenu={(chat) => c.setDeleteConfirmChat(chat)}
        deleteConfirmChat={c.deleteConfirmChat}
        onCancelDeleteConfirm={() => c.setDeleteConfirmChat(null)}
        deleteChatMutation={c.deleteChatMutation}
      />
    </div>
  )
}
