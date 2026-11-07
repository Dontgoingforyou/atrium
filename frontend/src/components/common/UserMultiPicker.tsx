import { useMemo } from 'react'
import type { PortalUserShort } from '../../api/usersApi'
import { usePortalUserDirectory } from '../../hooks/usePortalUserDirectory'
import { SearchableMultiPicker } from './SearchableMultiPicker'
import type { SearchablePickerOption } from './searchablePickerUtils'
import { getUserDisplayLabel } from '../../utils/userLabel'
import { renderUserOption } from './userPickerOption'
import styles from '@/styles/modules/ui/SearchablePicker.module.css'

interface UserMultiPickerProps {
  value: string[]
  onChange: (subs: string[]) => void
  placeholder?: string
  limit?: number
  chipsPosition?: 'below' | 'right'
  lockedValues?: string[]
  invalid?: boolean
  readOnly?: boolean
}

export function UserMultiPicker({
  value,
  onChange,
  placeholder = 'Добавить исполнителя…',
  limit = 500,
  chipsPosition,
  lockedValues,
  invalid = false,
  readOnly = false,
}: UserMultiPickerProps) {
  const { users, isPending: usersPending, isError: usersError } = usePortalUserDirectory({ limit })

  const options: SearchablePickerOption[] = useMemo(
    () =>
      (users ?? []).map((u) => ({
        value: u.sub,
        label: getUserDisplayLabel(u),
        secondary: u.email,
      })),
    [users],
  )

  const userBySub = useMemo(() => {
    const m = new Map<string, PortalUserShort>()
    for (const u of users ?? []) {
      m.set(u.sub, u)
    }
    return m
  }, [users])

  return (
    <div className={invalid ? styles.invalidWrap : undefined}>
      <SearchableMultiPicker
        value={value}
        onChange={onChange}
        options={options}
        placeholder={placeholder}
        loading={usersPending}
        error={usersError}
        minDropdownWidth={420}
        chipsAriaLabel="Выбранные исполнители"
        chipsPosition={chipsPosition}
        lockedValues={lockedValues}
        readOnly={readOnly}
        renderOption={(opt, pick, a11y) => renderUserOption(opt, pick, a11y, userBySub.get(opt.value))}
      />
    </div>
  )
}
