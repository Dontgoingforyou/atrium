import type { PortalUser } from '../../types/chat'
import { PresenceInline } from '../../components/chat/common/PresenceInline'
import { UserAvatar } from '../../components/ui/UserAvatar'
import sidebar from '@/styles/modules/chat/ChatsPageSidebar.module.css'
import thread from '@/styles/modules/chat/ChatsPageThread.module.css'

type Props = {
  pickerSearch: string
  onPickerSearchChange: (v: string) => void
  filteredUsers: PortalUser[]
  userMap: Record<string, string>
  dmError: string | null
  usersError?: string | null
  isPending: boolean
  onSelectUser: (sub: string) => void
}

export function ChatsSidebarDmPicker({
  pickerSearch,
  onPickerSearchChange,
  filteredUsers,
  userMap,
  dmError,
  usersError = null,
  isPending,
  onSelectUser,
}: Props) {
  return (
    <>
      <div className={sidebar.pickerSearchWrap}>
        <input
          type="search"
          className={sidebar.pickerSearch}
          placeholder="Поиск пользователя…"
          aria-label="Поиск пользователя"
          value={pickerSearch}
          onChange={(e) => onPickerSearchChange(e.target.value)}
          autoFocus
        />
        {usersError ? <p className={thread.dmError}>{usersError}</p> : null}
        {dmError ? <p className={thread.dmError}>{dmError}</p> : null}
      </div>
      <div className={sidebar.pickerList}>
        {isPending && <p className={sidebar.listEmpty}>Открываем диалог…</p>}
        {!isPending && !usersError && filteredUsers.length === 0 && (
          <p className={sidebar.listEmpty}>Пользователи не найдены</p>
        )}
        {!isPending &&
          !usersError &&
          filteredUsers.map((u: PortalUser) => {
            const name = userMap[u.sub] ?? u.sub
            return (
              <button
                key={u.sub}
                type="button"
                className={sidebar.pickerItem}
                onClick={() => onSelectUser(u.sub)}
              >
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
              </button>
            )
          })}
      </div>
    </>
  )
}
