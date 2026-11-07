import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { createTask, patchTaskWithCas } from '../../api/tasks/tasksApi'
import { isApiConflictError } from '../../api/apiConflict'
import { useDelayedActionContext } from '../../hooks/useDelayedActionContext'
import { useNotifyToast } from '../../hooks/useNotifyToast'
import { useScheduleTaskDelete } from '../../hooks/useScheduleTaskDelete'
import { useKanbanBoardWebSocket } from './useKanbanBoardWebSocket'
import { useTasksPageQueries } from './useTasksPageQueries'
import { useTasksBoardPrefMutations } from './useTasksBoardPrefMutations'
import { useTasksReorderMutation } from './useTasksReorderMutation'
import { useTasksColumnMutations } from './useTasksColumnMutations'
import type { PortalTask } from '../../types/task'
import { userCanDeleteTask, userCanEditTask } from '../../domain/tasks/taskPermissions'
import { resolveDefaultTaskAssigneeSubs } from '../../domain/tasks/taskAssigneeDefaults'
import { shouldPlayTaskDoneSuccess } from '../../domain/tasks/taskColumns'
import { userFacingMessageFromUnknown } from '../../utils/apiUserMessage'
import { playUiSound } from '../../utils/sound/uiSounds'
import { invalidatePortalSearchQueries } from '@/utils/search/invalidatePortalSearch'
import { PORTAL_TASKS_ROOT_QUERY_KEY } from './tasksQueryKeys'
import { useAuthStore } from '../../store/authStore'
import { isUserManagerOrAdmin } from '@/domain/auth/authRoles'
import { setRepeatedSearchParam } from '../../utils/searchParamsUtils'
import { filterTasksByPriorityWithFamily } from '../../domain/kanban/kanbanDisplayCommon'
import {
  computeEffectiveTaskScope,
  parseAssigneeSubsFromSearchParams,
  parseTaskStatusesFromSearchParams,
  parseTaskTagIdsFromSearchParams,
  parseTaskPrioritiesFromSearchParams,
  parseDoneThisMonthFromSearchParams,
  parseKpiOpenFromSearchParams,
  parseNoAssigneeFromSearchParams,
  parseOverdueOnlyFromSearchParams,
  parseTaskScopeFromUrl,
  parseTasksView,
  parseTaskIdFromSearchParams,
  setTruthySearchParam,
  urlIndicatesTeamScope,
  type TaskScope,
  type TasksView,
} from './tasksPageUrl'

export function useTasksPageController() {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const user = useAuthStore((s) => s.user)
  const [searchParams, setSearchParams] = useSearchParams()

  const initialView = parseTasksView(searchParams.get('view'))
  const [view, setView] = useState<TasksView>(initialView)

  // URL — единственный источник правды для scope/фильтров (без промежуточного useState +
  // отложенного useEffect-синхронизации, см. useSpecialistsPageFilters — идентичный паттерн).
  const taskScope: TaskScope = parseTaskScopeFromUrl(searchParams.get('scope'))
  const canUseTeamScope = !!user && isUserManagerOrAdmin(user)
  const urlTeam = urlIndicatesTeamScope(searchParams.get('scope'))
  const effectiveTaskScope = computeEffectiveTaskScope({ urlTeam, taskScope, canUseTeamScope })

  const filterStatuses = parseTaskStatusesFromSearchParams(searchParams)
  const filterTagIds = parseTaskTagIdsFromSearchParams(searchParams)
  const filterPriorities = parseTaskPrioritiesFromSearchParams(searchParams)
  const assigneeSubs = parseAssigneeSubsFromSearchParams(searchParams)
  const overdueOnly = parseOverdueOnlyFromSearchParams(searchParams)
  const doneThisMonth = parseDoneThisMonthFromSearchParams(searchParams)
  const noAssignee = parseNoAssigneeFromSearchParams(searchParams)
  const kpiOpenOnly = parseKpiOpenFromSearchParams(searchParams)

  function setFilterStatuses(next: string[]) {
    setSearchParams(setRepeatedSearchParam(searchParams, 'status', next), { replace: true })
  }

  function setFilterTagIds(next: string[]) {
    setSearchParams(setRepeatedSearchParam(searchParams, 'tag_id', next), { replace: true })
  }

  function setFilterPriorities(next: string[]) {
    setSearchParams(setRepeatedSearchParam(searchParams, 'priority', next), { replace: true })
  }

  function setAssigneeSubs(next: string[]) {
    const p = setRepeatedSearchParam(searchParams, 'assignee_sub', next)
    p.delete('assignee')
    setSearchParams(p, { replace: true })
  }

  function setOverdueOnly(next: boolean) {
    setSearchParams(setTruthySearchParam(searchParams, 'overdue', next), { replace: true })
  }

  function setDoneThisMonth(next: boolean) {
    setSearchParams(setTruthySearchParam(searchParams, 'done_this_month', next), { replace: true })
  }

  function setNoAssignee(next: boolean) {
    setSearchParams(setTruthySearchParam(searchParams, 'no_assignee', next), { replace: true })
  }

  function setKpiOpenOnly(next: boolean) {
    setSearchParams(setTruthySearchParam(searchParams, 'kpi_open', next), { replace: true })
  }

  const [showAllHiddenColumns, setShowAllHiddenColumns] = useState(false)
  const [personalBoardPanelOpen, setPersonalBoardPanelOpen] = useState(false)
  const [highlightTaskId, setHighlightTaskId] = useState<string | null>(null)
  const highlightClearRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useKanbanBoardWebSocket(view === 'kanban')

  const isManager = canUseTeamScope

  const {
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
  } = useTasksPageQueries(
    {
      filterStatuses,
      filterTagIds,
      filterPriorities,
      assigneeSubs,
      overdueOnly,
      doneThisMonth,
      noAssignee,
      kpiOpenOnly,
      effectiveTaskScope,
    },
    view,
  )

  const {
    putBoardPrefMutation,
    handlePersonalColumnReorder,
    toggleHiddenColumn,
    toggleSubtasksFlat,
    toggleHideSubtasks,
    clearColumnReorderTimer,
  } = useTasksBoardPrefMutations({ boardPrefQueryKey, boardPref })

  const {
    updateColumnMutation,
    createColumnMutation,
    deleteColumnMutation,
    scheduleTaskColumnDelete,
  } = useTasksColumnMutations()

  useEffect(() => {
    return () => {
      if (highlightClearRef.current) clearTimeout(highlightClearRef.current)
      clearColumnReorderTimer()
    }
  }, [clearColumnReorderTimer])

  useEffect(() => {
    const taskIdFromUrl = parseTaskIdFromSearchParams(searchParams)
    if (!taskIdFromUrl) return
    navigate(`/tasks/${taskIdFromUrl}`, { replace: true })
  }, [searchParams, navigate])

  function flashKanbanTask(taskId: string) {
    if (highlightClearRef.current) clearTimeout(highlightClearRef.current)
    setHighlightTaskId(taskId)
    highlightClearRef.current = setTimeout(() => {
      setHighlightTaskId(null)
      highlightClearRef.current = null
    }, 900)
  }

  const canEditColumns = canUseTeamScope
  const canEditKpi = !!user?.is_portal_admin

  const canEditTask = useCallback(
    (task: PortalTask) => userCanEditTask(task, user?.sub ?? '', !!user?.is_portal_admin),
    [user?.sub, user?.is_portal_admin],
  )

  const canDeleteTask = useCallback(
    (task: PortalTask) =>
      userCanDeleteTask(
        task,
        user?.sub ?? '',
        !!user?.is_portal_admin,
        Boolean(user && isUserManagerOrAdmin(user)),
      ),
    [user],
  )

  const notifyToast = useNotifyToast()

  const patchMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) => {
      const lists = queryClient.getQueriesData<PortalTask[]>({ queryKey: PORTAL_TASKS_ROOT_QUERY_KEY })
      let cachedVersion: number | undefined
      for (const [, list] of lists) {
        const found = list?.find((t) => t.id === id)
        if (found?.version != null) {
          cachedVersion = found.version
          break
        }
      }
      return patchTaskWithCas(id, { status }, cachedVersion)
    },
    onSuccess: (_data, vars) => {
      const previous = queryClient
        .getQueriesData<PortalTask[]>({ queryKey: PORTAL_TASKS_ROOT_QUERY_KEY })
        .flatMap(([, list]) => list ?? [])
        .find((t) => t.id === vars.id)
      if (previous && shouldPlayTaskDoneSuccess(previous.status, vars.status, columns)) {
        playUiSound('success')
      }
      void queryClient.invalidateQueries({ queryKey: PORTAL_TASKS_ROOT_QUERY_KEY })
      flashKanbanTask(vars.id)
    },
    onError: (e: unknown) => {
      if (isApiConflictError(e)) {
        void queryClient.invalidateQueries({ queryKey: PORTAL_TASKS_ROOT_QUERY_KEY })
      }
      notifyToast(userFacingMessageFromUnknown(e), { tone: 'error' })
    },
  })

  const reorderMutation = useTasksReorderMutation({
    tasksQueryKey,
    columns,
    onReorderSuccess: flashKanbanTask,
  })

  const createTaskMutation = useMutation({
    mutationFn: ({ title, status, assignee_subs }: { title: string; status: string; assignee_subs?: string[] }) =>
      createTask({ title, status, ...(assignee_subs?.length ? { assignee_subs } : {}) }),
    onSuccess: (task) => {
      queryClient.setQueryData<PortalTask[]>(tasksQueryKey, (prev) => {
        if (!prev) return [task]
        if (prev.some((t) => t.id === task.id)) return prev
        return [task, ...prev]
      })
      void queryClient.invalidateQueries({ queryKey: PORTAL_TASKS_ROOT_QUERY_KEY })
      invalidatePortalSearchQueries(queryClient)
    },
    onError: (e: unknown) => notifyToast(userFacingMessageFromUnknown(e), { tone: 'error' }),
  })

  const {
    pendingList: undoPending,
    undo: undoDelayed,
    optimisticallyHiddenIds,
  } = useDelayedActionContext()
  const { scheduleTaskDelete: scheduleTaskDeleteShared, deleteMutation: deleteTaskMutation } =
    useScheduleTaskDelete()

  const visibleTasks = useMemo(() => {
    if (!tasks) return undefined
    let result = optimisticallyHiddenIds.size === 0 ? tasks : tasks.filter((t) => !optimisticallyHiddenIds.has(t.id))
    if (filterPriorities.length > 0) {
      result = filterTasksByPriorityWithFamily(result, filterPriorities)
    }
    return result
  }, [tasks, optimisticallyHiddenIds, filterPriorities])

  function scheduleTaskDelete(taskId: string) {
    const previous = queryClient.getQueryData<PortalTask[]>(tasksQueryKey)
    scheduleTaskDeleteShared({
      taskId,
      patchListCache: () => {
        queryClient.setQueryData<PortalTask[]>(tasksQueryKey, (prev) =>
          prev ? prev.filter((t) => t.id !== taskId) : [],
        )
      },
      revertListCache: () => {
        if (previous) queryClient.setQueryData(tasksQueryKey, previous)
      },
    })
  }

  async function handleCreateTaskInColumn(title: string, status: string): Promise<string> {
    const assignee_subs = resolveDefaultTaskAssigneeSubs(effectiveTaskScope, assigneeSubs, user?.sub)
    const task = await createTaskMutation.mutateAsync({ title, status, assignee_subs })
    notifyToast('Задача создана')
    return task.id
  }

  function setScopeMy() {
    const next = new URLSearchParams(searchParams)
    next.delete('scope')
    next.delete('assignee')
    next.delete('assignee_sub')
    setSearchParams(next, { replace: true })
  }

  function setScopeTeam() {
    const next = new URLSearchParams(searchParams)
    next.set('scope', 'team')
    setSearchParams(next, { replace: true })
  }

  const hasActiveFilters =
    filterStatuses.length > 0 ||
    filterTagIds.length > 0 ||
    filterPriorities.length > 0 ||
    overdueOnly ||
    doneThisMonth ||
    noAssignee ||
    kpiOpenOnly ||
    (effectiveTaskScope === 'team' && assigneeSubs.length > 0)

  function resetFilters() {
    const next = new URLSearchParams(searchParams)
    next.delete('status')
    next.delete('tag_id')
    next.delete('priority')
    next.delete('assignee')
    next.delete('assignee_sub')
    next.delete('overdue')
    next.delete('done_this_month')
    next.delete('no_assignee')
    next.delete('kpi_open')
    setSearchParams(next, { replace: true })
  }

  return {
    user,
    view,
    setView,
    effectiveTaskScope,
    isManager,
    filterStatuses,
    setFilterStatuses,
    filterTagIds,
    setFilterTagIds,
    filterPriorities,
    setFilterPriorities,
    assigneeSubs,
    setAssigneeSubs,
    overdueOnly,
    setOverdueOnly,
    doneThisMonth,
    setDoneThisMonth,
    noAssignee,
    setNoAssignee,
    kpiOpenOnly,
    setKpiOpenOnly,
    showAllHiddenColumns,
    setShowAllHiddenColumns,
    personalBoardPanelOpen,
    setPersonalBoardPanelOpen,
    highlightTaskId,
    tags,
    columns,
    sortedColumns,
    boardPref,
    portalUsersForKanban,
    tasks: visibleTasks,
    isPending,
    isError,
    error,
    putBoardPrefMutation,
    patchMutation,
    reorderMutation,
    updateColumnMutation,
    createColumnMutation,
    deleteColumnMutation,
    createTaskMutation,
    deleteTaskMutation,
    handleCreateTaskInColumn,
    handlePersonalColumnReorder,
    toggleHiddenColumn,
    toggleSubtasksFlat,
    toggleHideSubtasks,
    canEditColumns,
    canEditKpi,
    canEditTask,
    canDeleteTask,
    setScopeMy,
    setScopeTeam,
    hasActiveFilters,
    resetFilters,
    undoPending,
    undoDelayed,
    scheduleTaskDelete,
    scheduleTaskColumnDelete,
  }
}
