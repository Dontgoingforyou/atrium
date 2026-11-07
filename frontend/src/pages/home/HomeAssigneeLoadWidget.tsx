import { useState } from 'react'
import { Link } from 'react-router'
import { UserAvatar } from '../../components/ui/UserAvatar'
import { usePortalUserDirectory } from '../../hooks/usePortalUserDirectory'
import type { TeamAssigneeLoad } from '../../types/home'
import styles from '@/styles/modules/home/HomeAssignee.module.css'
import pageStyles from '@/styles/modules/home/HomePage.module.css'
import { homeDashboardNavState } from '../tasks/taskBackNav'
import { buildTeamAssigneeOverdueTasksPath } from '../tasks/tasksPageUrl'
import { extraAssigneeLoadRows, hiddenCount, visibleAssigneeLoadRows } from './homeAssigneeTasks'
import { HOME_ASSIGNEE_TILE_LIMIT } from './homeQueryKeys'

type Props = {
  rows: TeamAssigneeLoad[]
  selectedSub: string | null
  onSelect: (sub: string) => void
}

export function HomeAssigneeLoadWidget({ rows, selectedSub, onSelect }: Props) {
  // Те же URL, что в шапке/задачах — иначе каждый fetchHome даёт новый MinIO-presign и сбрасывает кэш браузера
  const { getAvatarProps } = usePortalUserDirectory()
  const [expanded, setExpanded] = useState(false)
  const rest = hiddenCount(rows.length, HOME_ASSIGNEE_TILE_LIMIT)
  const previewRows = visibleAssigneeLoadRows(rows, HOME_ASSIGNEE_TILE_LIMIT, false)
  const extraRows = extraAssigneeLoadRows(rows, HOME_ASSIGNEE_TILE_LIMIT)

  function renderTile(r: TeamAssigneeLoad) {
    const avatar = getAvatarProps(r.assignee_sub, {
      label: r.display_name ?? undefined,
    })
    const label = avatar.label
    const selected = selectedSub === r.assignee_sub
    const overdueHint = r.overdue_count > 0 ? `, ${r.overdue_count} просрочено` : ''
    return (
      <button
        key={r.assignee_sub}
        type="button"
        className={`${styles.assigneeTile} ${selected ? styles.assigneeTileSelected : ''}`}
        title={`${label}: ${r.open_count} открытых задач (KPI)${overdueHint}`}
        aria-pressed={selected}
        onClick={() => onSelect(r.assignee_sub)}
      >
        <span className={styles.assigneeTileHeader}>
          <UserAvatar
            label={label}
            imageUrl={avatar.imageUrl}
            focalX={avatar.focalX}
            focalY={avatar.focalY}
            size="sm"
            loading="eager"
          />
          <span className={styles.assigneeName}>{label}</span>
        </span>
        <span className={styles.assigneeTileStats}>
          <span className={styles.assigneeOpen}>{r.open_count} всего</span>
          {r.overdue_count > 0 ? (
            <Link
              to={buildTeamAssigneeOverdueTasksPath(r.assignee_sub)}
              state={homeDashboardNavState()}
              className={`${styles.assigneeOverdue} ${styles.assigneeTileOverdue} ${styles.assigneeOverdueLink}`}
              title={`Открыть просроченные задачи: ${label}`}
              aria-label={`Открыть просроченные задачи: ${label}`}
              onClick={(e) => e.stopPropagation()}
            >
              {r.overdue_count} просрочено
            </Link>
          ) : null}
        </span>
      </button>
    )
  }

  return (
    <div className={styles.assigneeLoad}>
      <span className={styles.assigneeLoadTitle}>Нагрузка по исполнителям</span>
      <div>
        <div className={styles.assigneeLoadList}>{previewRows.map(renderTile)}</div>
        {extraRows.length > 0 ? (
          <div
            className={`${styles.assigneeLoadMoreShell} ${expanded ? styles.assigneeLoadMoreShellOpen : ''}`}
            aria-hidden={!expanded}
            inert={!expanded}
          >
            <div className={styles.assigneeLoadMoreInner}>
              <div className={styles.assigneeLoadList}>{extraRows.map(renderTile)}</div>
            </div>
          </div>
        ) : null}
      </div>
      {rest > 0 ? (
        <p className={styles.assigneeLoadMore}>
          <button
            type="button"
            className={`${pageStyles.widgetLink} ${styles.assigneeLoadMoreBtn}`}
            aria-expanded={expanded}
            aria-label={expanded ? 'Свернуть список исполнителей' : 'Показать остальных исполнителей'}
            onClick={() => setExpanded((open) => !open)}
          >
            {expanded ? 'Свернуть' : `ещё ${rest}`}
          </button>
        </p>
      ) : null}
    </div>
  )
}
