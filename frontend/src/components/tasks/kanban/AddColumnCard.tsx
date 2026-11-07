import { useRef, useState } from 'react'
import type { TaskColumnCreate } from '../../../types/task'
import { IconPlus, IconX } from '../../icons/portalIcons'
import styles from '@/styles/modules/tasks/TasksPageKanbanColumns.module.css'

export function AddColumnCard({
  onAdd,
  canEditKpi = false,
}: {
  onAdd: (data: TaskColumnCreate) => void
  canEditKpi?: boolean
}) {
  const [isOpen, setIsOpen] = useState(false)
  const [title, setTitle] = useState('')
  const [color, setColor] = useState('#6131cf')
  const [excludeFromKpi, setExcludeFromKpi] = useState(false)
  const titleRef = useRef<HTMLInputElement>(null)

  function handleOpen() {
    setIsOpen(true)
    setTimeout(() => titleRef.current?.focus(), 0)
  }

  function handleCancel() {
    setIsOpen(false)
    setTitle('')
    setColor('#6131cf')
    setExcludeFromKpi(false)
  }

  function handleAdd() {
    const t = title.trim()
    if (!t) return
    const statusKey = `col_${Math.random().toString(36).slice(2, 10)}`
    onAdd({
      title: t,
      status_key: statusKey,
      color,
      ...(canEditKpi ? { exclude_from_kpi: excludeFromKpi } : {}),
    })
    handleCancel()
  }

  if (!isOpen) {
    return (
      <button type="button" className={styles.addColumnCard} onClick={handleOpen}>
        <span className={styles.addColumnPlus} aria-hidden>
          <IconPlus />
        </span>
        <span>Добавить колонку</span>
      </button>
    )
  }

  return (
    <div className={`${styles.addColumnCard} ${styles.addColumnCardOpen}`}>
      <p className={styles.addColumnFormTitle}>Новая колонка</p>
      <input
        ref={titleRef}
        type="text"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        placeholder="Название колонки"
        className={styles.addColumnTitleInput}
        onKeyDown={(e) => {
          if (e.key === 'Enter') handleAdd()
          if (e.key === 'Escape') handleCancel()
        }}
      />
      <div className={styles.addColumnColorRow}>
        <input
          type="color"
          value={color}
          onChange={(e) => setColor(e.target.value)}
          className={styles.kanbanColumnColorPicker}
          title="Цвет колонки"
        />
        <span className={styles.addColumnColorLabel}>Цвет</span>
      </div>
      {canEditKpi ? (
        <label className={styles.kanbanColumnKpiToggle}>
          <input
            type="checkbox"
            checked={excludeFromKpi}
            onChange={(e) => setExcludeFromKpi(e.target.checked)}
          />
          <span>Исключить из KPI</span>
        </label>
      ) : null}
      <div className={styles.addColumnButtons}>
        <button type="button" className={styles.kanbanFormSaveBtn} onClick={handleAdd}>
          ✓ Создать
        </button>
        <button type="button" className={styles.kanbanFormCancelBtn} onClick={handleCancel} aria-label="Отмена">
          <IconX />
        </button>
      </div>
    </div>
  )
}
