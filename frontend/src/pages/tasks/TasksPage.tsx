import { useMemo } from 'react'
import { useLocation, useNavigate } from 'react-router'
import { userFacingMessageFromUnknown } from '../../utils/apiUserMessage'
import { KanbanBoard } from '../../components/tasks/kanban/KanbanBoard'
import { TaskRow } from '../../components/tasks/TaskRow'
import { orderTasksForListView } from '../../domain/kanban/kanbanDisplayCommon'
import { resolveDefaultTaskAssigneeSubs } from '../../domain/tasks/taskAssigneeDefaults'
import { IconPlus } from '../../components/icons/portalIcons'
import styles from '@/styles/modules/tasks/TasksPageShell.module.css'
import { TaskBackButton } from './TaskBackButton'
import {
  buildTaskOpenNavState,
  isHomeDashboardNav,
  pickTaskBackNavState,
  resolveTaskBackNav,
} from './taskBackNav'
import { useTasksPageController } from './useTasksPageController'
import { useAuthStore } from '../../store/authStore'
import { TasksFiltersPanel } from './TasksFiltersPanel'
import { TasksPersonalBoardPanel } from './TasksPersonalBoardPanel'

export function TasksPage() {
  const c = useTasksPageController()
  const navigate = useNavigate()
  const location = useLocation()
  const user = useAuthStore((s) => s.user)
  const backNavState = buildTaskOpenNavState(location)
  const dashboardBackNav = isHomeDashboardNav(location.state)
    ? resolveTaskBackNav(pickTaskBackNavState(location.state))
    : null

  const listTasksOrdered = useMemo(
    () => (c.tasks ? orderTasksForListView(c.tasks) : []),
    [c.tasks],
  )

  const initialAssigneeSubs = useMemo(
    () => resolveDefaultTaskAssigneeSubs(c.effectiveTaskScope, c.assigneeSubs, user?.sub),
    [c.effectiveTaskScope, c.assigneeSubs, user?.sub],
  )

  const exportFilters = useMemo(
    () => ({
      mine_only: c.effectiveTaskScope === 'my' ? true : undefined,
      assignee_sub:
        c.effectiveTaskScope === 'team' && c.assigneeSubs.length > 0 ? c.assigneeSubs : undefined,
    }),
    [c.effectiveTaskScope, c.assigneeSubs],
  )

  function openCreateModal(status?: string) {
    navigate('/tasks/new', {
      state: { initialStatus: status ?? 'todo', initialAssigneeSubs },
    })
  }

  return (
    <div className={styles.pageRoot}>
      <div className={`page-header ${styles.pageHeader}`}>
        {dashboardBackNav ? (
          <TaskBackButton
            label={dashboardBackNav.label}
            to={dashboardBackNav.to}
            state={dashboardBackNav.state}
          />
        ) : null}
        <h1 className="page-title">Задачи</h1>
        <button
          type="button"
          onClick={() => openCreateModal()}
          className={`btn-primary ${styles.headerCreateBtn}`}
          data-tour="tasks-create"
        >
          <IconPlus size={16} />
          Создать задачу
        </button>
      </div>

      <TasksFiltersPanel
        isManager={c.isManager}
        effectiveTaskScope={c.effectiveTaskScope}
        setScopeMy={c.setScopeMy}
        setScopeTeam={c.setScopeTeam}
        assigneeSubs={c.assigneeSubs}
        setAssigneeSubs={c.setAssigneeSubs}
        hasActiveFilters={c.hasActiveFilters}
        resetFilters={c.resetFilters}
        filterStatuses={c.filterStatuses}
        setFilterStatuses={c.setFilterStatuses}
        filterTagIds={c.filterTagIds}
        setFilterTagIds={c.setFilterTagIds}
        tags={c.tags}
        filterPriorities={c.filterPriorities}
        setFilterPriorities={c.setFilterPriorities}
        overdueOnly={c.overdueOnly}
        setOverdueOnly={c.setOverdueOnly}
        doneThisMonth={c.doneThisMonth}
        setDoneThisMonth={c.setDoneThisMonth}
        noAssignee={c.noAssignee}
        setNoAssignee={c.setNoAssignee}
        kpiOpenOnly={c.kpiOpenOnly}
        setKpiOpenOnly={c.setKpiOpenOnly}
        view={c.view}
        setView={c.setView}
      />

      {c.isPending ? (
        <p className="text-muted">Загрузка…</p>
      ) : c.isError ? (
        <p className="text-danger">{userFacingMessageFromUnknown(c.error)}</p>
      ) : (
        <div className={styles.boardHost} data-tour="tasks-kanban">
          {c.view === 'kanban' ? (
            <>
              <TasksPersonalBoardPanel
                open={c.personalBoardPanelOpen}
                setOpen={c.setPersonalBoardPanelOpen}
                showAllHiddenColumns={c.showAllHiddenColumns}
                setShowAllHiddenColumns={c.setShowAllHiddenColumns}
                sortedColumns={c.sortedColumns}
                boardPref={c.boardPref}
                boardPrefPending={c.putBoardPrefMutation.isPending}
                toggleHiddenColumn={c.toggleHiddenColumn}
                toggleSubtasksFlat={c.toggleSubtasksFlat}
                toggleHideSubtasks={c.toggleHideSubtasks}
              />
              <KanbanBoard
                tasks={c.tasks ?? []}
                columns={c.columns}
                boardPref={c.boardPref ?? null}
                showAllHiddenColumns={c.showAllHiddenColumns}
                isUpdating={c.reorderMutation.isPending}
                canEditColumns={c.canEditColumns}
                canEditKpi={c.canEditKpi}
                allowPersonalColumnDrag
                assigneeDirectory={c.portalUsersForKanban}
                highlightTaskId={c.highlightTaskId}
                canDeleteTask={c.canDeleteTask}
                onDeleteTask={(taskId) => c.scheduleTaskDelete(taskId)}
                canEditTask={c.canEditTask}
                kanbanScrollStorageKey={`tasks-kanban-${c.effectiveTaskScope}`}
                scrollToFirstNonEmptyColumn={
                  c.overdueOnly || c.doneThisMonth || c.noAssignee || c.kpiOpenOnly
                }
                exportFilters={exportFilters}
                onReorder={(id, newStatus, anchor) =>
                  c.reorderMutation.mutate({ taskId: id, newStatus, anchor })
                }
                onUpdateColumn={(id, data) => c.updateColumnMutation.mutate({ id, data })}
                onDeleteColumn={(id) => c.scheduleTaskColumnDelete(id)}
                onCreateColumn={(data) => c.createColumnMutation.mutate(data)}
                onReorderColumns={c.handlePersonalColumnReorder}
                onCreateTask={c.handleCreateTaskInColumn}
                onOpenTask={(taskId) => navigate(`/tasks/${taskId}`, { state: backNavState })}
              />
            </>
          ) : !c.tasks || c.tasks.length === 0 ? (
            <p className="text-muted">Задач не найдено</p>
          ) : (
            <div className={styles.taskListColumn}>
              {listTasksOrdered.map((task) => (
                <TaskRow
                  key={task.id}
                  task={task}
                  columns={c.columns}
                  isSubtask={Boolean(task.parent_task_id)}
                  canEdit={c.canEditTask(task)}
                  navState={backNavState}
                  onStatusChange={(status) => c.patchMutation.mutate({ id: task.id, status })}
                  isUpdating={c.patchMutation.isPending}
                />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
