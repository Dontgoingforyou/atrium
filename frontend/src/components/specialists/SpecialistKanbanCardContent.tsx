import type { ManagerSpecialistEntry, SpecialistColumn } from '../../types/specialist'
import { UserAvatar } from '../ui/UserAvatar'
import { UserChipBySub } from '../ui/UserChip'
import { IconX } from '../icons/portalIcons'
import { SpecialistKanbanColumnSelect } from './SpecialistKanbanColumnSelect'
import styles from '@/styles/modules/specialists/SpecialistsPage.module.css'

interface Props {
  entry: ManagerSpecialistEntry
  columns?: SpecialistColumn[]
  showRemove?: boolean
  onRemove?: (specialistSub: string) => void
  canChangeColumn?: boolean
  columnChanging?: boolean
  onColumnChange?: (columnKey: string) => void
}

export function SpecialistKanbanCardContent({
  entry,
  columns = [],
  showRemove = false,
  onRemove,
  canChangeColumn = false,
  columnChanging = false,
  onColumnChange,
}: Props) {
  const label = entry.display_name ?? entry.specialist_sub

  return (
    <>
      <div className={styles.cardHeader}>
        <UserAvatar label={label} imageUrl={entry.avatar_url} size="sm" />
        <span className={styles.cardName}>{label}</span>
        {showRemove && onRemove ? (
          <button
            type="button"
            className={styles.cardRemoveBtn}
            title="Убрать с доски"
            aria-label="Убрать с доски"
            draggable={false}
            onPointerDown={(e) => e.stopPropagation()}
            onClick={(e) => {
              e.stopPropagation()
              onRemove(entry.specialist_sub)
            }}
          >
            <IconX />
          </button>
        ) : null}
      </div>

      <div className={styles.cardMeta}>
        <span className={styles.cardMetaLabel}>Направление</span>
        <span className={styles.cardMetaValue}>{entry.status_title || '—'}</span>
      </div>

      {entry.manager_display_name ? (
        <div className={styles.cardMeta}>
          <span className={styles.cardMetaLabel}>
            {entry.manager_display_name.includes(',') ? 'Менеджеры' : 'Менеджер'}
          </span>
          <span className={styles.cardMetaValue}>
            <UserChipBySub
              sub={entry.manager_sub}
              labelOverride={entry.manager_display_name}
            />
          </span>
        </div>
      ) : null}

      {canChangeColumn && onColumnChange ? (
        <div className={styles.cardFooter}>
          <SpecialistKanbanColumnSelect
            columns={columns}
            currentColumnKey={entry.column_key}
            disabled={columnChanging}
            onChange={onColumnChange}
          />
        </div>
      ) : null}
    </>
  )
}
