import type { PortalUser } from '../../types/chat'
import { PresenceInline } from '../../components/chat/common/PresenceInline'
import { UserAvatar } from '../../components/ui/UserAvatar'
import sidebar from '@/styles/modules/chat/ChatsPageSidebar.module.css'
import thread from '@/styles/modules/chat/ChatsPageThread.module.css'

type Props = {
  groupTitle: string
  onGroupTitleChange: (v: string) => void
  pickerSearch: string
  onPickerSearchChange: (v: string) => void
  groupError: string | null
  usersError?: string | null
  filteredUsers: PortalUser[]
  userMap: Record<string, string>
  groupSelected: Record<string, boolean>
  onMemberToggle: (sub: string, checked: boolean) => void
  canSubmitGroup: boolean
  isPending: boolean
  onSubmit: () => void
}

export function ChatsSidebarGroupForm({
  groupTitle,
  onGroupTitleChange,
  pickerSearch,
  onPickerSearchChange,
  groupError,
  usersError = null,
  filteredUsers,
  userMap,
  groupSelected,
  onMemberToggle,
  canSubmitGroup,
  isPending,
  onSubmit,
}: Props) {
  return (
    <div className={thread.groupForm}>
        <label className={thread.groupLabel}>
          Название группы
          <input
            className={thread.groupTitleInput}
            value={groupTitle}
            onChange={(e) => onGroupTitleChange(e.target.value)}
            placeholder="Например, Команда проекта"
          />
        </label>
        <div className={thread.groupFormSearchWrap}>
          <input
            type="search"
            className={sidebar.pickerSearch}
            placeholder="Поиск для добавления участников…"
            aria-label="Поиск участников группы"
            value={pickerSearch}
            onChange={(e) => onPickerSearchChange(e.target.value)}
          />
          {groupError ? <p className={thread.dmError}>{groupError}</p> : null}
          {usersError ? <p className={thread.dmError}>{usersError}</p> : null}
        </div>
        <div className={sidebar.pickerList}>
          {usersError ? null : filteredUsers.map((u: PortalUser) => {
            const name = userMap[u.sub] ?? u.sub
            const checked = Boolean(groupSelected[u.sub])
            return (
              <label key={u.sub} className={thread.groupMemberRow}>
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={(e) => onMemberToggle(u.sub, e.target.checked)}
                />
                <UserAvatar
                  size={36}
                  label={name}
                  imageUrl={u.avatar_url ?? undefined}
                  focalX={u.avatar_focal_x}
                  focalY={u.avatar_focal_y}
                  className={thread.pickerRowAvatar}
                />
                <span className={thread.pickerItemText}>
                  <span className={thread.pickerName}>{name}</span>
                  <PresenceInline presence={u.presence} lastSeenAt={u.last_seen_at} />
                </span>
              </label>
            )
          })}
        </div>
        <button
          type="button"
          className={thread.createGroupBtn}
          disabled={!canSubmitGroup || isPending}
          onClick={onSubmit}
        >
          {isPending ? 'Создаём…' : 'Создать группу'}
        </button>
    </div>
  )
}
