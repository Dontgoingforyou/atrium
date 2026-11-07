import type { ReactNode } from 'react'
import { useThemeStore } from '../../store/themeStore'
import { getEffectiveTheme, getTagChipStyle, type TagChipBorderVariant } from '../../utils/tags/tagColor'

type Props = {
  /** Цвет из БД */
  storedColor: string
  children: ReactNode
  className?: string
  active?: boolean
  border?: TagChipBorderVariant
}

/** Чип тега с адаптацией цвета под тему зрителя. */
export function TagChip({ storedColor, children, className, active, border = 'default' }: Props) {
  const storeTheme = useThemeStore((s) => s.theme)
  const theme = getEffectiveTheme(storeTheme)
  return (
    <span className={className} style={getTagChipStyle(storedColor, theme, { active, border })}>
      {children}
    </span>
  )
}
