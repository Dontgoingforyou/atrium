import type { PortalUser } from '../../../types/chat'
import { UserAvatar } from '../../ui/UserAvatar'
import { PresenceInline } from '../common/PresenceInline'
import chrome from '@/styles/modules/chat/FloatingDmWidgetChrome.module.css'
import picker from '@/styles/modules/chat/FloatingDmWidgetPicker.module.css'

type Props = {
  groupTitle: string
  pickerSearch: string
  groupSelected: Record<string, boolean>
  filteredUsers: PortalUser[]
  userMap: Record<string, string>
  error: string | null
  isPending: boolean
  canSubmit: boolean
  onGroupTitleChange: (v: string) => void
  onPickerSearchChange: (v: string) => void
  onMemberToggle: (sub: string, checked: boolean) => void
  onSubmit: () => void
  avatarClassName?: string
}

export function CreateGroupPanel({
  groupTitle,
  pickerSearch,
  groupSelected,
  filteredUsers,
  userMap,
  error,
  isPending,
  canSubmit,
  onGroupTitleChange,
  onPickerSearchChange,
  onMemberToggle,
  onSubmit,
  avatarClassName,
}: Props) {
  const avatarCls = avatarClassName ?? chrome.pickerAvatar
  return (
    <div className={picker.groupForm}>
      <label className={picker.groupLabel}>
        Название группы
        <input
          className={picker.groupTitleInput}
          value={groupTitle}
          onChange={(e) => onGroupTitleChange(e.target.value)}
          placeholder="Например, Команда проекта"
        />
      </label>
      <div className={picker.pickerSearchWrap}>
        <input
          type="search"
          className={picker.pickerSearch}
          placeholder="Поиск для добавления участников…"
          value={pickerSearch}
          onChange={(e) => onPickerSearchChange(e.target.value)}
        />
        {error ? <p className={picker.dmError}>{error}</p> : null}
      </div>
      <div className={picker.pickerList}>
        {filteredUsers.map((u: PortalUser) => {
          const name = userMap[u.sub] ?? u.sub
          const checked = Boolean(groupSelected[u.sub])
          return (
            <label key={u.sub} className={picker.groupMemberRow}>
              <input
                type="checkbox"
                checked={checked}
                onChange={(e) => onMemberToggle(u.sub, e.target.checked)}
              />
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
            </label>
          )
        })}
      </div>
      <button
        type="button"
        className={picker.createGroupBtn}
        disabled={!canSubmit || isPending}
        onClick={onSubmit}
      >
        {isPending ? 'Создаём…' : 'Создать группу'}
      </button>
    </div>
  )
}
