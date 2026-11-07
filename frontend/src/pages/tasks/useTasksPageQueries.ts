import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { listTags } from '../../api/tags/tagsApi'
import { PORTAL_TAGS_QUERY_KEY, PORTAL_TASK_COLUMNS_QUERY_KEY, portalUsersQueryOptions } from '../../api/queryKeys'
import { getTaskBoardPref, listTaskColumns, listTasks } from '../../api/tasks/tasksApi'
import type { PortalTag } from '../../types/document'
import type { TaskScope, TasksView } from './tasksPageUrl'
import { TASK_BOARD_PREF_QUERY_KEY, tasksListQueryKey } from './tasksQueryKeys'

export type TasksPageFilters = {
  filterStatuses: string[]
  filterTagIds: string[]
  filterPriorities: string[]
  assigneeSubs: string[]
  overdueOnly: boolean
  doneThisMonth: boolean
  noAssignee: boolean
  kpiOpenOnly: boolean
  effectiveTaskScope: TaskScope
}

export function useTasksPageQueries(filters: TasksPageFilters, view: TasksView) {
  const {
    filterStatuses,
    filterTagIds,
    filterPriorities,
    assigneeSubs,
    overdueOnly,
    doneThisMonth,
    noAssignee,
    kpiOpenOnly,
    effectiveTaskScope,
  } = filters

  const { data: tags } = useQuery<PortalTag[]>({
    queryKey: PORTAL_TAGS_QUERY_KEY,
    queryFn: listTags,
  })

  const { data: columns = [] } = useQuery({
    queryKey: PORTAL_TASK_COLUMNS_QUERY_KEY,
    queryFn: () => listTaskColumns(),
  })

  const sortedColumns = useMemo(
    () => [...columns].sort((a, b) => a.position - b.position),
    [columns],
  )

  const boardPrefQueryKey = TASK_BOARD_PREF_QUERY_KEY

  const { data: boardPref } = useQuery({
    queryKey: boardPrefQueryKey,
    queryFn: () => getTaskBoardPref(),
  })

  const { data: portalUsersForKanban } = useQuery(portalUsersQueryOptions())

  const tasksQueryKey = tasksListQueryKey({
    filterStatuses,
    filterTagIds,
    filterPriorities,
    assigneeSubs,
    overdueOnly,
    doneThisMonth,
    noAssignee,
    kpiOpenOnly,
    taskScope: effectiveTaskScope,
  })

  const { data: tasks, isPending, isError, error } = useQuery({
    queryKey: tasksQueryKey,
    queryFn: () =>
      listTasks({
        mine_only: effectiveTaskScope === 'my' ? true : undefined,
        assignee_sub:
          effectiveTaskScope === 'team' && assigneeSubs.length > 0 ? assigneeSubs : undefined,
        status: filterStatuses.length > 0 ? filterStatuses : undefined,
        tag_id: filterTagIds.length > 0 ? filterTagIds : undefined,
        priority: filterPriorities.length > 0 ? filterPriorities : undefined,
        overdue_only: overdueOnly || undefined,
        done_this_month: doneThisMonth || undefined,
        no_assignee: noAssignee || undefined,
        kpi_open_only: kpiOpenOnly || undefined,
        limit: 200,
      }),
    refetchInterval: view === 'kanban' ? 30_000 : false,
  })

  return {
    tags,
    columns,
    sortedColumns,
    boardPref,
    boardPrefQueryKey,
    portalUsersForKanban,
    tasks,
    tasksQueryKey,
    isPending,
    isError,
    error,
  }
}
