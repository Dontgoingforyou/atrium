import { useCallback, useEffect, useId, useState, type ReactNode } from 'react'

import styles from '@/styles/modules/tasks/TaskDetailPage.module.css'
import {
  GUIDED_TOUR_TASK_PANEL_EVENT,
  type GuidedTourTaskPanelDetail,
} from '../../../onboarding/ensureTourDemoTask'
import {
  computeInitialOpen,
  persistOpen,
  resolveAutoOpenState,
  type TaskDetailPanelId,
} from './taskDetailPanelState'

/**
 * Секция карточки на странице задачи: можно свернуть.
 *
 * `contentCount` (опционально) — число элементов в секции (комментарии/ссылки/подзадачи и т.п.).
 * Начальная открытость и авто-обновление при загрузке/изменении `contentCount` считаются
 * через `taskDetailPanelState` (content-driven панели — по наличию содержимого, «История» —
 * всегда свёрнута по умолчанию и т.д.). Пользователь может переключить панель вручную
 * в любую сторону в любой момент — этот выбор перестаёт перекрываться авто-обновлением
 * до размонтирования компонента (см. `touched`).
 *
 * `tourAnchor` — значение `data-tour` для guided tour; событие
 * `guided-tour-task-panel` с тем же якорем принудительно раскрывает секцию.
 */
export function TaskDetailPanel({
  panelId,
  title,
  contentCount,
  onOpenChange,
  tourAnchor,
  children,
}: {
  panelId: TaskDetailPanelId
  title: string
  contentCount?: number
  onOpenChange?: (open: boolean) => void
  /** Якорь guided tour (`data-tour`), если секция участвует в онбординге. */
  tourAnchor?: string
  children: ReactNode
}) {
  const titleId = useId()
  const bodyId = useId()
  const [open, setOpen] = useState(() => computeInitialOpen(panelId, contentCount))
  const [touched, setTouched] = useState(false)
  const contentCountNorm = contentCount ?? 0
  const nextAutoKey = `${panelId}:${contentCountNorm}`
  const [autoKey, setAutoKey] = useState(nextAutoKey)

  // Подстройка open при смене contentCount — во время рендера (React docs:
  // «Adjusting state when a prop changes»), без эффекта, чтобы не ловить
  // react-hooks/set-state-in-effect. После ручного toggle авто больше не трогаем.
  if (!touched && nextAutoKey !== autoKey) {
    setAutoKey(nextAutoKey)
    const auto = resolveAutoOpenState(panelId, contentCountNorm)
    if (auto !== undefined) {
      setOpen(auto)
    }
  }

  const toggle = useCallback(() => {
    setTouched(true)
    setOpen((o) => {
      const n = !o
      persistOpen(panelId, n)
      return n
    })
  }, [panelId])

  useEffect(() => {
    onOpenChange?.(open)
  }, [open, onOpenChange])

  useEffect(() => {
    if (!tourAnchor) return
    const onTourPanel = (event: Event) => {
      const detail = (event as CustomEvent<GuidedTourTaskPanelDetail>).detail
      if (!detail || detail.tourAnchor !== tourAnchor) return
      setTouched(true)
      setOpen(true)
      persistOpen(panelId, true)
    }
    document.addEventListener(GUIDED_TOUR_TASK_PANEL_EVENT, onTourPanel)
    return () => document.removeEventListener(GUIDED_TOUR_TASK_PANEL_EVENT, onTourPanel)
  }, [panelId, tourAnchor])

  return (
    <section
      className={`${styles.card} ${styles.sectionCard}`}
      aria-labelledby={titleId}
      {...(tourAnchor ? { 'data-tour': tourAnchor } : {})}
    >
      <button
        type="button"
        className={styles.taskPanelHeader}
        onClick={toggle}
        aria-expanded={open}
        aria-controls={bodyId}
        aria-label={open ? `Свернуть: ${title}` : `Развернуть: ${title}`}
      >
        <h2 className={styles.cardTitle} id={titleId}>
          {title}
        </h2>
        <span
          className={styles.taskPanelToggleIcon}
          aria-hidden
          data-state={open ? 'open' : 'closed'}
        >
          ▾
        </span>
      </button>
      <div
        id={bodyId}
        className={styles.taskPanelBodyShell}
        data-state={open ? 'open' : 'closed'}
        aria-hidden={!open ? true : undefined}
      >
        <div
          className={styles.taskPanelBodyInner}
          inert={!open || undefined}
        >
          {children}
        </div>
      </div>
    </section>
  )
}
