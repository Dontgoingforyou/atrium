import { useRef } from 'react'

import { THEME_OPTIONS, useThemeStore, type ThemeId } from '../../store/themeStore'
import styles from '@/styles/modules/layout/ThemeToggle.module.css'

function prefersReducedMotion(): boolean {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

function nextTheme(current: ThemeId): ThemeId {
  return current === 'light' ? 'dark' : 'light'
}

export function ThemeToggle() {
  const theme = useThemeStore((s) => s.theme)
  const setTheme = useThemeStore((s) => s.setTheme)
  const btnRef = useRef<HTMLButtonElement>(null)

  const current = THEME_OPTIONS.find((o) => o.id === theme)
  const label = current?.label ?? 'Тема'
  const buttonIcon = current?.icon ?? '☀️'

  function toggleTheme() {
    const next = nextTheme(theme)
    setTheme(next)

    const btn = btnRef.current
    if (prefersReducedMotion()) {
      btn?.classList.remove(styles.justToggled)
      return
    }
    if (btn) {
      btn.classList.remove(styles.justToggled)
      void btn.offsetHeight
      btn.classList.add(styles.justToggled)
      window.setTimeout(() => btn.classList.remove(styles.justToggled), 400)
    }
  }

  return (
    <div className={styles.wrap} data-tour="theme-toggle">
      <button
        ref={btnRef}
        type="button"
        className={styles.btn}
        title="Переключить тему оформления"
        aria-label={`Переключить тему (сейчас: ${label})`}
        onClick={toggleTheme}
      >
        {buttonIcon}
      </button>
    </div>
  )
}
