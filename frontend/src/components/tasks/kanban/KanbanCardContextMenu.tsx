import { useEffect, useRef } from 'react'

import styles from '@/styles/modules/tasks/TasksPageKanbanColumns.module.css'

type Position = { x: number; y: number }

/**
 * Контекстное меню карточки задачи (правый клик или кнопка «⋮» в углу карточки).
 *
 * Само состояние позиции/открытия держит родитель (`KanbanCard`); здесь —
 * только рендер по координатам + a11y: `role="menu"`, `role="menuitem"`,
 * закрытие по Escape и по клику вне, перенос фокуса в меню при открытии.
 */
export function KanbanCardContextMenu({
  position,
  canDelete,
  onClose,
  onOpen,
  onDelete,
}: {
  position: Position
  canDelete: boolean
  onClose: () => void
  onOpen: () => void
  onDelete: () => void
}) {
  const menuRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const onPointerDown = (e: PointerEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) onClose()
    }
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.stopPropagation()
        onClose()
      }
    }
    window.addEventListener('pointerdown', onPointerDown)
    window.addEventListener('keydown', onKey)
    const firstItem = menuRef.current?.querySelector<HTMLButtonElement>('button')
    firstItem?.focus()
    return () => {
      window.removeEventListener('pointerdown', onPointerDown)
      window.removeEventListener('keydown', onKey)
    }
  }, [onClose])

  return (
    <div
      ref={menuRef}
      className={styles.kanbanCtxMenu}
      style={{ position: 'fixed', top: position.y, left: position.x }}
      role="menu"
      aria-label="Действия с задачей"
      onPointerDown={(e) => e.stopPropagation()}
    >
      <button
        type="button"
        role="menuitem"
        className={styles.kanbanCtxMenuItem}
        onClick={() => {
          onClose()
          onOpen()
        }}
      >
        Открыть задачу
      </button>
      {canDelete ? (
        <button
          type="button"
          role="menuitem"
          className={styles.kanbanCtxMenuDelete}
          onClick={() => {
            onClose()
            onDelete()
          }}
        >
          Удалить задачу
        </button>
      ) : null}
    </div>
  )
}
