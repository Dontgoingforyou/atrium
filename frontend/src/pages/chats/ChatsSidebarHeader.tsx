import type { ChatsLeftView } from './useChatsPageController'
import sidebar from '@/styles/modules/chat/ChatsPageSidebar.module.css'
import thread from '@/styles/modules/chat/ChatsPageThread.module.css'

type Props = {
  leftView: ChatsLeftView
  sidebarTitle: string
  onBackToList: () => void
  onNewDm: () => void
  onNewGroup: () => void
}

export function ChatsSidebarHeader({
  leftView,
  sidebarTitle,
  onBackToList,
  onNewDm,
  onNewGroup,
}: Props) {
  return (
    <div className={sidebar.sidebarHeader}>
      {leftView !== 'list' ? (
        <button
          type="button"
          className={sidebar.backToListBtn}
          onClick={onBackToList}
          aria-label="К списку чатов"
        >
          ‹
        </button>
      ) : null}
      <span className={sidebar.sidebarTitle}>{sidebarTitle}</span>
      {leftView === 'list' ? (
        <div className={thread.headerActions} data-tour="chats-new">
          <button type="button" className={sidebar.newDmBtn} onClick={onNewDm}>
            + Диалог
          </button>
          <button type="button" className={thread.newGroupBtn} onClick={onNewGroup}>
            + Группа
          </button>
        </div>
      ) : null}
    </div>
  )
}
