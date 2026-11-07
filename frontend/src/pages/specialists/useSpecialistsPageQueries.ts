import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'

import { getSpecialistBoardPref, listBoardEntries, listSpecialistColumns } from '../../api/specialists/specialistsApi'
import { listPortalStudentSpecialists } from '../../api/usersApi'
import {
  enrichEntriesWithAllManagers,
  entryMatchesBoardFilters,
  filterBoardEntries,
  type SpecialistBoardFilters,
} from '../../domain/specialists/specialistCoManagers'
import { mergeSpecialistColumnOrder } from '../../domain/specialists/specialistBoardPref'
import {
  QK_BOARD_ROOT,
  QK_COLUMNS,
  QK_PREF,
} from '../../domain/specialists/specialistBoardCache'
import type { ManagerSpecialistEntry } from '../../types/specialist'
import type { SpecialistScope, SpecialistView } from './specialistsPageUrl'
import { SPECIALISTS_STUDENTS_ROOT_QUERY_KEY } from './specialistQueryKeys'

const QK_BOARD = QK_BOARD_ROOT
const QK_STUDENTS = SPECIALISTS_STUDENTS_ROOT_QUERY_KEY
const QK_BOARD_DIRECTORY = [...QK_BOARD, 'directory'] as const

export const SPECIALISTS_PAGE_SIZE = 50

interface CurrentUser {
  sub: string
  full_name?: string | null
  email?: string | null
  username?: string | null
  display_name?: string | null
}

interface Props {
  canAccess: boolean
  user: CurrentUser | null
  isAdmin: boolean
  scope: SpecialistScope
  view: SpecialistView
  boardFilters: SpecialistBoardFilters
  studentsOffset: number
}

/** Все `useQuery` страницы специалистов: доска, колонки, предпочтения, справочник студентов. */
export function useSpecialistsPageQueries({
  canAccess,
  user,
  isAdmin,
  scope,
  view,
  boardFilters,
  studentsOffset,
}: Props) {
  const boardScopeKey = scope === 'my' ? 'my' : 'all'
  const boardQueryKey = [...QK_BOARD, boardScopeKey, user?.sub] as const

  const { data: columns = [], isError: colsErr, error: colsError } = useQuery({
    queryKey: QK_COLUMNS,
    queryFn: listSpecialistColumns,
    enabled: canAccess,
  })

  const { data: boardPref } = useQuery({
    queryKey: QK_PREF,
    queryFn: getSpecialistBoardPref,
    enabled: canAccess && view === 'kanban',
  })

  const columnOrder = useMemo(
    () => mergeSpecialistColumnOrder(columns, boardPref),
    [columns, boardPref],
  )

  const {
    data: entries = [],
    isPending: boardPending,
    isError: boardErr,
    error: boardError,
  } = useQuery({
    queryKey: boardQueryKey,
    queryFn: () => {
      if (scope === 'my' && user?.sub) {
        return listBoardEntries(isAdmin ? { manager_sub: user.sub } : undefined)
      }
      if (scope === 'all') {
        return listBoardEntries({ directory: true })
      }
      return listBoardEntries()
    },
    enabled: canAccess,
  })

  const {
    data: directoryEntries = [],
    isError: directoryErr,
    error: directoryError,
  } = useQuery({
    queryKey: QK_BOARD_DIRECTORY,
    queryFn: () => listBoardEntries({ directory: true }),
    enabled: canAccess && scope === 'my',
  })

  const {
    data: studentsPage,
    isFetching: studentsFetching,
    isError: studentsErr,
    error: studentsError,
  } = useQuery({
    queryKey: [...QK_STUDENTS, studentsOffset],
    queryFn: () => listPortalStudentSpecialists({ limit: SPECIALISTS_PAGE_SIZE, skip: studentsOffset }),
    enabled: canAccess && scope === 'all' && view === 'list',
    staleTime: 60_000,
  })

  const allSpecialists = useMemo(() => studentsPage?.items ?? [], [studentsPage])
  const studentsTotal = studentsPage?.total ?? 0

  const directoryForFilters = scope === 'all' ? entries : directoryEntries

  const boardEntriesMy = useMemo(() => {
    if (scope !== 'my' || !user?.sub) return []
    return entries.filter((e: ManagerSpecialistEntry) => e.manager_sub === user.sub)
  }, [scope, entries, user])

  const filteredBoardEntriesMy = useMemo(
    () => filterBoardEntries(boardEntriesMy, boardFilters, directoryForFilters, 'my'),
    [boardEntriesMy, boardFilters, directoryForFilters],
  )

  const displayEntriesMy = useMemo(() => {
    if (!user?.sub) return filteredBoardEntriesMy
    return enrichEntriesWithAllManagers(filteredBoardEntriesMy, directoryForFilters, user.sub)
  }, [filteredBoardEntriesMy, directoryForFilters, user])

  const filteredBoardEntriesAll = useMemo(
    () => filterBoardEntries(entries, boardFilters, directoryForFilters, 'all'),
    [entries, boardFilters, directoryForFilters],
  )

  const columnTitleByKey = useMemo(
    () => new Map(columns.map((c) => [c.key, c.title])),
    [columns],
  )

  const attachmentsBySpecialistSub = useMemo(() => {
    const map = new Map<string, ManagerSpecialistEntry[]>()
    for (const e of entries) {
      const list = map.get(e.specialist_sub) ?? []
      list.push(e)
      map.set(e.specialist_sub, list)
    }
    return map
  }, [entries])

  const alreadyAddedSubs = useMemo(
    () => new Set(boardEntriesMy.map((e: ManagerSpecialistEntry) => e.specialist_sub)),
    [boardEntriesMy],
  )

  const onMyBoardSubs = useMemo(
    () =>
      new Set(
        entries
          .filter((e: ManagerSpecialistEntry) => e.manager_sub === user?.sub)
          .map((e: ManagerSpecialistEntry) => e.specialist_sub),
      ),
    [entries, user?.sub],
  )

  const filteredAllListStudents = useMemo(() => {
    const hasManagerFilter = boardFilters.managerSubs.length > 0
    const hasSpecialistFilter = boardFilters.specialistSubs.length > 0
    return allSpecialists.filter((s) => {
      if (hasSpecialistFilter && !boardFilters.specialistSubs.includes(s.sub)) return false
      if (!hasManagerFilter) return true
      const attachments = attachmentsBySpecialistSub.get(s.sub) ?? []
      return attachments.some((e) =>
        entryMatchesBoardFilters(e, boardFilters, directoryForFilters, 'all'),
      )
    })
  }, [allSpecialists, boardFilters, attachmentsBySpecialistSub, directoryForFilters])

  return {
    boardQueryKey,
    columns,
    boardPref: boardPref ?? null,
    columnOrder,
    entries,
    boardPending,
    colsErr,
    colsError,
    boardErr,
    boardError,
    directoryForFilters,
    boardEntriesMy,
    displayEntriesMy,
    boardEntriesAllKanban: filteredBoardEntriesAll,
    columnTitleByKey,
    attachmentsBySpecialistSub,
    alreadyAddedSubs,
    onMyBoardSubs,
    allSpecialists,
    filteredAllListStudents,
    studentsTotal,
    studentsFetching,
    studentsErr,
    studentsError,
    directoryErr,
    directoryError,
  }
}
