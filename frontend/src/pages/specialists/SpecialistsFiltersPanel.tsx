import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'

import { AddableFilterBar, type AddableFilterField } from '../../components/common/AddableFilterBar'
import { UserMultiPicker } from '../../components/common/UserMultiPicker'
import { SpecialistMultiPicker } from '../../components/common/SpecialistMultiPicker'
import { portalUsersQueryOptions } from '../../api/queryKeys'
import { listPortalStudentSpecialists } from '../../api/usersApi'
import { getUserDisplayLabel } from '../../utils/userLabel'
import type { SpecialistScope, SpecialistView } from './specialistsPageUrl'
import { specialistStudentsFilterQueryKey } from './specialistQueryKeys'
import taskShell from '@/styles/modules/tasks/TasksPageShell.module.css'

type Props = {
  scope: SpecialistScope
  setScope: (scope: SpecialistScope) => void
  view: SpecialistView
  setView: (view: SpecialistView) => void
  hasActiveFilters: boolean
  resetFilters: () => void
  filterManagerSubs: string[]
  setFilterManagerSubs: (next: string[]) => void
  filterSpecialistSubs: string[]
  setFilterSpecialistSubs: (next: string[]) => void
}

export function SpecialistsFiltersPanel({
  scope,
  setScope,
  view,
  setView,
  hasActiveFilters,
  resetFilters,
  filterManagerSubs,
  setFilterManagerSubs,
  filterSpecialistSubs,
  setFilterSpecialistSubs,
}: Props) {
  const { data: portalUsers } = useQuery({
    ...portalUsersQueryOptions(500),
    enabled: filterManagerSubs.length > 0,
  })
  const { data: specialistsPage } = useQuery({
    queryKey: specialistStudentsFilterQueryKey(),
    queryFn: () => listPortalStudentSpecialists({ limit: 200, skip: 0 }),
    staleTime: 60_000,
    enabled: filterSpecialistSubs.length > 0,
  })

  const managerLabels = useMemo(() => {
    const bySub = new Map((portalUsers ?? []).map((u) => [u.sub, getUserDisplayLabel(u)]))
    return filterManagerSubs.map((sub) => bySub.get(sub) ?? sub)
  }, [filterManagerSubs, portalUsers])

  const specialistLabels = useMemo(() => {
    const bySub = new Map(
      (specialistsPage?.items ?? []).map((u) => [u.sub, getUserDisplayLabel(u)]),
    )
    return filterSpecialistSubs.map((sub) => bySub.get(sub) ?? sub)
  }, [filterSpecialistSubs, specialistsPage])

  const fields: AddableFilterField[] = useMemo(
    () => [
      {
        id: 'manager',
        label: 'Менеджеры',
        hasValues: filterManagerSubs.length > 0,
        selectedLabels: managerLabels,
        onClear: () => setFilterManagerSubs([]),
        renderPicker: () => (
          <UserMultiPicker
            value={filterManagerSubs}
            onChange={setFilterManagerSubs}
            placeholder="Все — начните вводить имя…"
          />
        ),
      },
      {
        id: 'specialist',
        label: 'Специалисты',
        hasValues: filterSpecialistSubs.length > 0,
        selectedLabels: specialistLabels,
        onClear: () => setFilterSpecialistSubs([]),
        renderPicker: () => (
          <SpecialistMultiPicker
            value={filterSpecialistSubs}
            onChange={setFilterSpecialistSubs}
            placeholder="Все — начните вводить имя…"
          />
        ),
      },
    ],
    [
      filterManagerSubs,
      setFilterManagerSubs,
      managerLabels,
      filterSpecialistSubs,
      setFilterSpecialistSubs,
      specialistLabels,
    ],
  )

  return (
    <div className={taskShell.controls} data-tour="specialists-filters">
      <div className={taskShell.controlsMain}>
        <div
          className={taskShell.scopeToggle}
          role="group"
          aria-label="Область специалистов"
          data-tour="specialists-scope"
        >
          <button
            type="button"
            className={scope === 'my' ? taskShell.scopeToggleActive : taskShell.scopeToggleBtn}
            onClick={() => setScope('my')}
          >
            Мои специалисты
          </button>
          <button
            type="button"
            className={scope === 'all' ? taskShell.scopeToggleActive : taskShell.scopeToggleBtn}
            onClick={() => setScope('all')}
          >
            Все специалисты
          </button>
        </div>
        <AddableFilterBar
          fields={fields}
          hasActiveFilters={hasActiveFilters}
          resetFilters={resetFilters}
        />
      </div>
      <div className={taskShell.viewToggle} role="group" aria-label="Вид" data-tour="specialists-view">
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
