import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'

import { AddableFilterBar, type AddableFilterField } from '../../components/common/AddableFilterBar'
import { SearchableMultiPicker } from '../../components/common/SearchableMultiPicker'
import { UserMultiPicker } from '../../components/common/UserMultiPicker'
import { portalUsersQueryOptions } from '../../api/queryKeys'
import type { PortalTag } from '../../types/document'
import type { TaskPriority, TaskStatus } from '../../types/task'
import {
  DONE_THIS_MONTH_FILTER_LABEL,
  DONE_THIS_MONTH_FILTER_SELECTED_LABEL,
  KPI_OPEN_FILTER_LABEL,
  KPI_OPEN_FILTER_SELECTED_LABEL,
  NO_ASSIGNEE_FILTER_LABEL,
  NO_ASSIGNEE_FILTER_SELECTED_LABEL,
  OVERDUE_FILTER_LABEL,
  OVERDUE_FILTER_SELECTED_LABEL,
  PRIORITY_LABELS,
  STATUS_LABELS,
} from '../../domain/tasks/taskUi'
import type { TaskScope } from './tasksPageUrl'
import taskShell from '@/styles/modules/tasks/TasksPageShell.module.css'

type View = 'kanban' | 'list'

type Props = {
  isManager: boolean
  effectiveTaskScope: TaskScope
  setScopeMy: () => void
  setScopeTeam: () => void
  assigneeSubs: string[]
  setAssigneeSubs: (next: string[]) => void
  hasActiveFilters: boolean
  resetFilters: () => void
  filterStatuses: string[]
  setFilterStatuses: (next: string[]) => void
  filterTagIds: string[]
  setFilterTagIds: (next: string[]) => void
  tags: PortalTag[] | undefined
  filterPriorities: string[]
  setFilterPriorities: (next: string[]) => void
  overdueOnly: boolean
  setOverdueOnly: (next: boolean) => void
  doneThisMonth: boolean
  setDoneThisMonth: (next: boolean) => void
  noAssignee: boolean
  setNoAssignee: (next: boolean) => void
  kpiOpenOnly: boolean
  setKpiOpenOnly: (next: boolean) => void
  view: View
  setView: (view: View) => void
}

function userDisplayLabel(u: {
  display_name?: string | null
  email?: string | null
  username?: string | null
  sub: string
}): string {
  return u.display_name || u.email || u.username || u.sub
}

export function TasksFiltersPanel({
  isManager,
  effectiveTaskScope,
  setScopeMy,
  setScopeTeam,
  assigneeSubs,
  setAssigneeSubs,
  hasActiveFilters,
  resetFilters,
  filterStatuses,
  setFilterStatuses,
  filterTagIds,
  setFilterTagIds,
  tags,
  filterPriorities,
  setFilterPriorities,
  overdueOnly,
  setOverdueOnly,
  doneThisMonth,
  setDoneThisMonth,
  noAssignee,
  setNoAssignee,
  kpiOpenOnly,
  setKpiOpenOnly,
  view,
  setView,
}: Props) {
  const teamAssignees = isManager && effectiveTaskScope === 'team'
  const { data: portalUsers } = useQuery({
    ...portalUsersQueryOptions(500),
    enabled: teamAssignees || assigneeSubs.length > 0,
  })

  const assigneeLabels = useMemo(() => {
    const bySub = new Map((portalUsers ?? []).map((u) => [u.sub, userDisplayLabel(u)]))
    return assigneeSubs.map((sub) => bySub.get(sub) ?? sub)
  }, [assigneeSubs, portalUsers])

  const tagNameById = useMemo(() => {
    const m = new Map<string, string>()
    for (const tag of tags ?? []) m.set(tag.id, tag.name)
    return m
  }, [tags])

  const fields: AddableFilterField[] = useMemo(() => {
    const statusOptions = (Object.keys(STATUS_LABELS) as TaskStatus[]).map((s) => ({
      value: s,
      label: STATUS_LABELS[s],
    }))
    const list: AddableFilterField[] = [
      {
        id: 'status',
        label: 'Статусы',
        hasValues: filterStatuses.length > 0,
        selectedLabels: filterStatuses.map((s) => STATUS_LABELS[s as TaskStatus] ?? s),
        onClear: () => setFilterStatuses([]),
        renderPicker: () => (
          <SearchableMultiPicker
            value={filterStatuses}
            onChange={setFilterStatuses}
            options={statusOptions}
            placeholder="Все — начните вводить статус…"
            chipsAriaLabel="Выбранные статусы"
          />
        ),
      },
      {
        id: 'tag',
        label: 'Теги',
        hasValues: filterTagIds.length > 0,
        selectedLabels: filterTagIds.map((id) => tagNameById.get(id) ?? id),
        onClear: () => setFilterTagIds([]),
        renderPicker: () => (
          <SearchableMultiPicker
            value={filterTagIds}
            onChange={setFilterTagIds}
            options={(tags ?? []).map((tag) => ({ value: tag.id, label: tag.name }))}
            placeholder="Все — начните вводить тег…"
            chipsAriaLabel="Выбранные теги"
          />
        ),
      },
      {
        id: 'priority',
        label: 'Приоритеты',
        hasValues: filterPriorities.length > 0,
        selectedLabels: filterPriorities.map((p) => PRIORITY_LABELS[p as TaskPriority] ?? p),
        onClear: () => setFilterPriorities([]),
        renderPicker: () => (
          <div className={taskShell.priorityFilterBtns} role="group" aria-label="Фильтр по приоритету">
            {(Object.keys(PRIORITY_LABELS) as TaskPriority[]).map((p) => (
              <button
                key={p}
                type="button"
                className={`${taskShell.priorityFilterBtn} ${filterPriorities.includes(p) ? taskShell.priorityFilterBtnActive : ''}`}
                onClick={() => {
                  const next = filterPriorities.includes(p)
                    ? filterPriorities.filter((x) => x !== p)
                    : [...filterPriorities, p]
                  setFilterPriorities(next)
                }}
              >
                {PRIORITY_LABELS[p]}
              </button>
            ))}
          </div>
        ),
      },
      {
        id: 'kpi_open',
        label: KPI_OPEN_FILTER_LABEL,
        hasValues: kpiOpenOnly,
        selectedLabels: kpiOpenOnly ? [KPI_OPEN_FILTER_SELECTED_LABEL] : [],
        defaultActive: kpiOpenOnly,
        openOnAdd: false,
        onActivate: () => setKpiOpenOnly(true),
        onClear: () => setKpiOpenOnly(false),
      },
      {
        id: 'overdue',
        label: OVERDUE_FILTER_LABEL,
        hasValues: overdueOnly,
        selectedLabels: overdueOnly ? [OVERDUE_FILTER_SELECTED_LABEL] : [],
        defaultActive: overdueOnly,
        openOnAdd: false,
        onActivate: () => setOverdueOnly(true),
        onClear: () => setOverdueOnly(false),
      },
      {
        id: 'done_this_month',
        label: DONE_THIS_MONTH_FILTER_LABEL,
        hasValues: doneThisMonth,
        selectedLabels: doneThisMonth ? [DONE_THIS_MONTH_FILTER_SELECTED_LABEL] : [],
        defaultActive: doneThisMonth,
        openOnAdd: false,
        onActivate: () => setDoneThisMonth(true),
        onClear: () => setDoneThisMonth(false),
      },
      {
        id: 'no_assignee',
        label: NO_ASSIGNEE_FILTER_LABEL,
        hasValues: noAssignee,
        selectedLabels: noAssignee ? [NO_ASSIGNEE_FILTER_SELECTED_LABEL] : [],
        defaultActive: noAssignee,
        openOnAdd: false,
        onActivate: () => setNoAssignee(true),
        onClear: () => setNoAssignee(false),
      },
      {
        id: 'assignee',
        label: 'Исполнители',
        hasValues: assigneeSubs.length > 0,
        selectedLabels: assigneeLabels,
        isAvailable: teamAssignees,
        defaultActive: teamAssignees,
        onClear: () => setAssigneeSubs([]),
        renderPicker: () => (
          <UserMultiPicker
            value={assigneeSubs}
            onChange={setAssigneeSubs}
            placeholder="Все — оставьте пустым или добавьте людей…"
          />
        ),
      },
    ]
    return list
  }, [
    filterStatuses,
    setFilterStatuses,
    filterTagIds,
    setFilterTagIds,
    tags,
    tagNameById,
    filterPriorities,
    setFilterPriorities,
    overdueOnly,
    setOverdueOnly,
    doneThisMonth,
    setDoneThisMonth,
    noAssignee,
    setNoAssignee,
    kpiOpenOnly,
    setKpiOpenOnly,
    assigneeSubs,
    setAssigneeSubs,
    assigneeLabels,
    teamAssignees,
  ])

  return (
    <div className={taskShell.controls} data-tour="tasks-filters">
      <div className={taskShell.controlsMain}>
        {isManager && (
          <div
            className={taskShell.scopeToggle}
            role="group"
            aria-label="Область задач"
            data-tour="tasks-scope"
          >
            <button
              type="button"
              className={effectiveTaskScope === 'my' ? taskShell.scopeToggleActive : taskShell.scopeToggleBtn}
              onClick={setScopeMy}
            >
              Мои задачи
            </button>
            <button
              type="button"
              className={effectiveTaskScope === 'team' ? taskShell.scopeToggleActive : taskShell.scopeToggleBtn}
              onClick={setScopeTeam}
            >
              Задачи команды
            </button>
          </div>
        )}
        <AddableFilterBar
          fields={fields}
          hasActiveFilters={hasActiveFilters}
          resetFilters={resetFilters}
        />
      </div>
      <div className={taskShell.viewToggle} role="group" aria-label="Вид" data-tour="tasks-view">
        <button
          type="button"
          className={view === 'kanban' ? taskShell.viewToggleActive : taskShell.viewToggleBtn}
          onClick={() => setView('kanban')}
        >
          Канбан
        </button>
        <button
          type="button"
          className={view === 'list' ? taskShell.viewToggleActive : taskShell.viewToggleBtn}
          onClick={() => setView('list')}
        >
          Список
        </button>
      </div>
    </div>
  )
}
