import { useState } from 'react'
import { useSearchParams } from 'react-router'

import { type SpecialistBoardFilters } from '../../domain/specialists/specialistCoManagers'
import {
  parseManagerSubsFromSearchParams,
  parseSpecialistSubsFromSearchParams,
  parseSpecialistScopeFromUrl,
  parseSpecialistViewFromUrl,
  specialistScopeToUrl,
  specialistViewToUrl,
  type SpecialistScope,
  type SpecialistView,
} from './specialistsPageUrl'

export interface SpecialistsPageFilters {
  searchParams: URLSearchParams
  setSearchParams: ReturnType<typeof useSearchParams>[1]
  scope: SpecialistScope
  view: SpecialistView
  subFromUrl: string | null
  filterManagerSubs: string[]
  filterSpecialistSubs: string[]
  boardFilters: SpecialistBoardFilters
  hasActiveFilters: boolean
  studentsOffset: number
  setStudentsOffset: React.Dispatch<React.SetStateAction<number>>
  setFilterManagerSubs: (subs: string[]) => void
  setFilterSpecialistSubs: (subs: string[]) => void
  resetFilters: () => void
  setScope: (next: SpecialistScope) => void
  setView: (next: SpecialistView) => void
}

/** Управление URL-параметрами страницы специалистов: scope, view, фильтры, пагинация. */
export function useSpecialistsPageFilters(): SpecialistsPageFilters {
  const [searchParams, setSearchParams] = useSearchParams()
  const [studentsOffset, setStudentsOffset] = useState(0)

  const scope: SpecialistScope = parseSpecialistScopeFromUrl(searchParams.get('scope'))
  const view: SpecialistView = parseSpecialistViewFromUrl(searchParams.get('view'))
  const subFromUrl = searchParams.get('sub')

  const filterManagerSubs = parseManagerSubsFromSearchParams(searchParams)
  const filterSpecialistSubs = parseSpecialistSubsFromSearchParams(searchParams)
  const boardFilters: SpecialistBoardFilters = {
    managerSubs: filterManagerSubs,
    specialistSubs: filterSpecialistSubs,
  }
  const hasActiveFilters = filterManagerSubs.length > 0 || filterSpecialistSubs.length > 0

  function setFilterManagerSubs(subs: string[]) {
    const p = new URLSearchParams(searchParams)
    p.delete('manager_sub')
    for (const sub of subs) p.append('manager_sub', sub)
    setSearchParams(p, { replace: true })
    setStudentsOffset(0)
  }

  function setFilterSpecialistSubs(subs: string[]) {
    const p = new URLSearchParams(searchParams)
    p.delete('specialist_sub')
    for (const sub of subs) p.append('specialist_sub', sub)
    setSearchParams(p, { replace: true })
    setStudentsOffset(0)
  }

  function resetFilters() {
    const p = new URLSearchParams(searchParams)
    p.delete('manager_sub')
    p.delete('specialist_sub')
    p.delete('q')
    setSearchParams(p, { replace: true })
    setStudentsOffset(0)
  }

  function setScope(next: SpecialistScope) {
    const p = new URLSearchParams(searchParams)
    if (next === 'my') p.delete('scope')
    else p.set('scope', specialistScopeToUrl(next))
    setSearchParams(p, { replace: true })
    setStudentsOffset(0)
  }

  function setView(next: SpecialistView) {
    const p = new URLSearchParams(searchParams)
    if (next === 'kanban') p.delete('view')
    else p.set('view', specialistViewToUrl(next))
    setSearchParams(p, { replace: true })
    setStudentsOffset(0)
  }

  return {
    searchParams,
    setSearchParams,
    scope,
    view,
    subFromUrl,
    filterManagerSubs,
    filterSpecialistSubs,
    boardFilters,
    hasActiveFilters,
    studentsOffset,
    setStudentsOffset,
    setFilterManagerSubs,
    setFilterSpecialistSubs,
    resetFilters,
    setScope,
    setView,
  }
}
