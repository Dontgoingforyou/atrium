import type { ManagerSpecialistEntry, SpecialistColumn } from '../../types/specialist'
import { UserAvatar } from '../../components/ui/UserAvatar'
import { UserChipBySub } from '../../components/ui/UserChip'
import styles from '@/styles/modules/specialists/SpecialistsPage.module.css'

type Props = {
  entries: ManagerSpecialistEntry[]
  columns: SpecialistColumn[]
  loading?: boolean
  onSelectEntry?: (entry: ManagerSpecialistEntry) => void
}

export function SpecialistsMyListSection({
  entries,
  columns,
  loading,
  onSelectEntry,
}: Props) {
  const columnTitleByKey = new Map(columns.map((c) => [c.key, c.title]))
  const sorted = [...entries].sort((a, b) => {
    const colA = columns.find((c) => c.key === a.column_key)?.position ?? 0
    const colB = columns.find((c) => c.key === b.column_key)?.position ?? 0
    if (colA !== colB) return colA - colB
    return a.position - b.position
  })

  if (loading) {
    return <p className="text-muted">Загрузка…</p>
  }

  if (sorted.length === 0) {
    return <p className="text-muted">На доске пока нет специалистов.</p>
  }

  return (
    <ul className={styles.allList}>
      {sorted.map((entry) => {
        const stage = columnTitleByKey.get(entry.column_key) ?? entry.column_key
        const label = entry.display_name ?? entry.specialist_sub
        return (
          <li key={entry.id} className={styles.allListRow}>
            <button
              type="button"
              className={styles.allListBtn}
              onClick={() => onSelectEntry?.(entry)}
            >
              <span className={styles.allListNamePrimary}>
                <UserAvatar
                  label={label}
                  imageUrl={entry.avatar_url}
                  size="sm"
                />
                {label}
              </span>
              {entry.status_title ? (
                <span className={styles.allListDirection}>{entry.status_title}</span>
              ) : null}
              <span className={styles.allListMeta}>
                {stage}
                {entry.manager_sub ? (
                  <>
                    {' · '}
                    <UserChipBySub
                      sub={entry.manager_sub}
                      labelOverride={entry.manager_display_name ?? undefined}
                    />
                  </>
                ) : null}
              </span>
            </button>
          </li>
        )
      })}
    </ul>
  )
}
