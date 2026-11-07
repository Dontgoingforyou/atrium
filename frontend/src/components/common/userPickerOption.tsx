import type { ReactNode } from 'react'

import { UserAvatar } from '../ui/UserAvatar'
import type { SearchablePickerOption } from './searchablePickerUtils'
import type { OptionA11yProps } from './SearchableMultiPicker'
import styles from '@/styles/modules/ui/SearchablePicker.module.css'

/** Поля пользователя, необходимые для отрисовки опции с аватаром. */
export type UserOptionAvatar = {
  avatar_url?: string | null
  avatar_focal_x?: number | null
  avatar_focal_y?: number | null
}

/**
 * Общий renderOption для пикеров пользователей: аватар + имя + secondary.
 * Используется в UserMultiPicker и SpecialistMultiPicker (dry.mdc).
 *
 * @param opt   опция пикера (value/label/secondary)
 * @param pick  колбэк выбора
 * @param a11y  A11y-атрибуты опции (role/id/aria-selected/data-active/onMouseEnter) —
 *              обязан применить к корневому элементу опции для клавиатурной навигации
 * @param user  пользователь для аватара (или undefined, если не найден)
 */
export function renderUserOption(
  opt: SearchablePickerOption,
  pick: () => void,
  a11y: OptionA11yProps,
  user: UserOptionAvatar | undefined,
): ReactNode {
  return (
    <div
      key={opt.value}
      className={styles.option}
      {...a11y}
      onMouseDown={(e) => {
        e.preventDefault()
        pick()
      }}
    >
      <UserAvatar
        size="sm"
        label={opt.label}
        imageUrl={user?.avatar_url}
        focalX={user?.avatar_focal_x}
        focalY={user?.avatar_focal_y}
      />
      <div className={styles.optionText}>
        <span className={styles.optionName}>{opt.label}</span>
        {opt.secondary && opt.secondary !== opt.label ? (
          <span className={styles.optionSecondary}>{opt.secondary}</span>
        ) : null}
      </div>
    </div>
  )
}
