import { useMemo } from 'react'
import { Link } from 'react-router'
import { useQuery } from '@tanstack/react-query'
import { listTasks } from '../../api/tasks/tasksApi'
import { SearchableMultiPicker } from '../../components/common/SearchableMultiPicker'
import { UserAvatar } from '../../components/ui/UserAvatar'
import { usePortalUserDirectory } from '../../hooks/usePortalUserDirectory'
import { sortedTaskColumns } from '../../domain/tasks/taskColumns'
import { userFacingMessageFromUnknown } from '../../utils/apiUserMessage'
import type { AssigneeHomeDrilldown } from '../../types/home'
import type { PortalTask, PortalTaskColumn } from '../../types/task'
import assigneeStyles from '@/styles/modules/home/HomeAssignee.module.css'
import styles from '@/styles/modules/home/HomePage.module.css'
import {
  homeDashboardNavState,
  readPortalMainScrollTop,
  type HomeDashboardListMode,
  type HomeDashboardRestore,
} from '../tasks/taskBackNav'
import { buildTeamAssigneeOpenTasksPath } from '../tasks/tasksPageUrl'
import {
  filterHomeAssigneeTasks,
  homeOnTrackCount,
  kpiActiveOpenStatusKeys,
  overduePreviewTasks,
} from './homeAssigneeTasks'
import { HOME_ASSIGNEE_TASKS_LIMIT, homeQueryKeys } from './homeQueryKeys'
import { HomeTaskRow } from './HomeTaskRow'

type Props = {
  data: AssigneeHomeDrilldown
  columns: PortalTaskColumn[]
  listMode: HomeDashboardListMode
  statusKeys: string[]
  onListModeChange: (mode: HomeDashboardListMode) => void
  onStatusKeysChange: (keys: string[]) => void
  onClose: () => void
}

function buildRestore(
  assigneeSub: string,
  listMode: HomeDashboardListMode,
  statusKeys: string[],
): HomeDashboardRestore {
  return {
    homeAssigneeSub: assigneeSub,
    homeScrollTop: readPortalMainScrollTop(),
    homeListMode: listMode,
    homeStatusKeys: statusKeys,
  }
}

export function HomeAssigneeDrilldownPanel({
  data,
  columns,
  listMode,
  statusKeys,
  onListModeChange,
  onStatusKeysChange,
  onClose,
}: Props) {
  const { getAvatarProps } = usePortalUserDirectory()
  const avatar = getAvatarProps(data.assignee_sub, {
    label: data.display_name ?? undefined,
  })
  const name = avatar.label
  const needsFetch = listMode !== 'all' || statusKeys.length > 0
  const onTrack = homeOnTrackCount(data.open_count, data.overdue_count)

  const filteredQuery = useQuery({
    queryKey: homeQueryKeys.assigneeTasks(data.assignee_sub, statusKeys, listMode),
    queryFn: () =>
      listTasks({
        assignee_sub: data.assignee_sub,
        status: statusKeys.length > 0 ? statusKeys : undefined,
        overdue_only: listMode === 'overdue' || undefined,
        limit: HOME_ASSIGNEE_TASKS_LIMIT,
      }),
    enabled: needsFetch,
  })

  const navState = useMemo(
    () => homeDashboardNavState(buildRestore(data.assignee_sub, listMode, statusKeys)),
    [data.assignee_sub, listMode, statusKeys],
  )

  const columnOptions = useMemo(
    () => sortedTaskColumns(columns).map((c) => ({ value: c.status_key, label: c.title })),
    [columns],
  )

  const flatTasks: PortalTask[] = useMemo(() => {
    if (!needsFetch) return []
    return filterHomeAssigneeTasks(filteredQuery.data ?? [], columns, listMode)
  }, [needsFetch, filteredQuery.data, listMode, columns])

  const overduePreview = useMemo(
    () => overduePreviewTasks(data.overdue_tasks_preview, columns),
    [data.overdue_tasks_preview, columns],
  )

  const truncated = Boolean(
    needsFetch &&
      !filteredQuery.isPending &&
      !filteredQuery.isError &&
      (filteredQuery.data?.length ?? 0) >= HOME_ASSIGNEE_TASKS_LIMIT,
  )

  function toggleMode(mode: 'open' | 'overdue') {
    onListModeChange(listMode === mode ? 'all' : mode)
  }

  return (
    <div className={assigneeStyles.assigneeDrilldown}>
      <div className={assigneeStyles.assigneeDrilldownHeader}>
        <UserAvatar
          label={name}
          imageUrl={avatar.imageUrl}
          focalX={avatar.focalX}
          focalY={avatar.focalY}
          size="md"
          loading="eager"
        />
        <div className={assigneeStyles.assigneeDrilldownHeaderMain}>
          <strong className={assigneeStyles.assigneeDrilldownName}>{name}</strong>
          <span className={assigneeStyles.assigneeDrilldownCounts}>
            <button
              type="button"
              className={`${assigneeStyles.assigneeDrilldownCountBtn} ${listMode === 'open' ? assigneeStyles.assigneeDrilldownCountBtnActive : ''}`}
              onClick={() => toggleMode('open')}
              aria-pressed={listMode === 'open'}
            >
              в срок: {onTrack}
            </button>
            {data.overdue_count > 0 ? (
              <>
                <span className={styles.textSmall} aria-hidden>
                  ·
                </span>
                <button
                  type="button"
                  className={`${assigneeStyles.assigneeDrilldownCountBtn} ${assigneeStyles.assigneeDrilldownCountBtnDanger} ${listMode === 'overdue' ? assigneeStyles.assigneeDrilldownCountBtnActive : ''}`}
                  onClick={() => toggleMode('overdue')}
                  aria-pressed={listMode === 'overdue'}
                >
                  просрочено: {data.overdue_count}
                </button>
              </>
            ) : null}
          </span>
        </div>
        <button
          type="button"
          className={`btn-secondary ${assigneeStyles.assigneeDrilldownClose}`}
          onClick={onClose}
        >
          Закрыть
        </button>
      </div>

      <div className={assigneeStyles.assigneeDrilldownFilters}>
        <SearchableMultiPicker
          value={statusKeys}
          onChange={onStatusKeysChange}
          options={columnOptions}
          placeholder="Фильтр по колонкам…"
          chipsAriaLabel="Выбранные колонки канбана"
          chipsPosition="right"
          hideChips={false}
        />
      </div>

      {needsFetch ? (
        filteredQuery.isPending ? (
          <p className={`text-muted ${styles.textSmall}`}>Загрузка задач…</p>
        ) : filteredQuery.isError ? (
          <p className="text-danger">{userFacingMessageFromUnknown(filteredQuery.error)}</p>
        ) : flatTasks.length === 0 ? (
          <p className={`text-muted ${styles.textSmall}`}>Нет задач по фильтру</p>
        ) : (
          <>
            <div className={styles.taskList}>
              {flatTasks.map((t) => (
                <HomeTaskRow key={t.id} task={t} columns={columns} navState={navState} />
              ))}
            </div>
            {truncated ? (
              <p className={`text-muted ${styles.textSmall}`}>
                Показаны первые {HOME_ASSIGNEE_TASKS_LIMIT}
              </p>
            ) : null}
          </>
        )
      ) : (
        <>
          {overduePreview.length > 0 ? (
            <>
              <p className={assigneeStyles.assigneeDrilldownSubtitle}>Просроченные</p>
              <div className={styles.taskList}>
                {overduePreview.map((t) => (
                  <HomeTaskRow key={t.id} task={t} columns={columns} navState={navState} />
                ))}
              </div>
            </>
          ) : null}
          {data.open_tasks_preview.length > 0 ? (
            <>
              <p className={assigneeStyles.assigneeDrilldownSubtitle}>Открытые</p>
              <div className={styles.taskList}>
                {data.open_tasks_preview.map((t) => (
                  <HomeTaskRow key={t.id} task={t} columns={columns} navState={navState} />
                ))}
              </div>
            </>
          ) : null}
        </>
      )}

      <Link
        to={buildTeamAssigneeOpenTasksPath(data.assignee_sub, kpiActiveOpenStatusKeys(columns))}
        state={navState}
        className={styles.widgetLink}
      >
        Все задачи исполнителя →
      </Link>
    </div>
  )
}
