import type { SpecialistBoardFilters } from '../../domain/specialists/specialistCoManagers'
import type { SpecialistScope, SpecialistView } from './specialistsPageUrl'
import { useSpecialistsPageMutations } from './useSpecialistsPageMutations'
import { SPECIALISTS_PAGE_SIZE, useSpecialistsPageQueries } from './useSpecialistsPageQueries'

export { SPECIALISTS_PAGE_SIZE }

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

/** Композиция данных и мутаций страницы специалистов (см. `useSpecialistsPageQueries` / `useSpecialistsPageMutations`). */
export function useSpecialistsPageData(props: Props) {
  const { boardQueryKey, ...queries } = useSpecialistsPageQueries(props)
  const mutations = useSpecialistsPageMutations({ columns: queries.columns, boardQueryKey })

  return {
    ...queries,
    ...mutations,
  }
}
