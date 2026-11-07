import type { PortalUser } from '../../../types/chat'
import { PresenceInline } from '../common/PresenceInline'
import { UserAvatar } from '../../ui/UserAvatar'
import chrome from '@/styles/modules/chat/FloatingDmWidgetChrome.module.css'
import picker from '@/styles/modules/chat/FloatingDmWidgetPicker.module.css'

type Props = {
  pickerSearch: string
  filteredUsers: PortalUser[]
  userMap: Record<string, string>
  isPending: boolean
  isError: boolean
  onPickerSearchChange: (v: string) => void
  onSelectUser: (sub: string) => void
  avatarClassName?: string
}

export function DmPickerPanel({
  pickerSearch,
  filteredUsers,
  userMap,
  isPending,
  isError,
  onPickerSearchChange,
  onSelectUser,
  avatarClassName,
}: Props) {
  const avatarCls = avatarClassName ?? chrome.pickerAvatar
  return (
    <>
      <div className={picker.pickerSearchWrap}>
        <input
          type="search"
          className={picker.pickerSearch}
          placeholder="Поиск пользователя…"
          value={pickerSearch}
          onChange={(e) => onPickerSearchChange(e.target.value)}
          autoFocus
        />
        {isError ? (
          <p className={picker.dmError}>Не удалось открыть диалог. Попробуйте ещё раз.</p>
        ) : null}
      </div>
      <div className={picker.pickerList}>
        {isPending && <p className={chrome.listEmpty}>Открываем диалог…</p>}
        {!isPending && filteredUsers.length === 0 && (
          <p className={chrome.listEmpty}>Пользователи не найдены</p>
        )}
        {!isPending &&
          filteredUsers.map((u) => {
            const name = userMap[u.sub] ?? u.sub
            return (
              <button
                key={u.sub}
                type="button"
                className={picker.pickerItem}
                onClick={() => onSelectUser(u.sub)}
              >
                <UserAvatar
                  size={36}
                  label={name}
                  imageUrl={u.avatar_url}
                  focalX={u.avatar_focal_x}
                  focalY={u.avatar_focal_y}
                  className={avatarCls}
                />
                <span className={picker.pickerItemText}>
                  <span className={picker.pickerName}>{name}</span>
                  <PresenceInline presence={u.presence} lastSeenAt={u.last_seen_at} />
                </span>
              </button>
            )
          })}
      </div>
    </>
  )
}
