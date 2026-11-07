import { parseRepeatedSearchParam } from '../../utils/searchParamsUtils'

export type SpecialistScope = 'my' | 'all'
export type SpecialistView = 'kanban' | 'list'

export function parseSpecialistScopeFromUrl(scopeParam: string | null): SpecialistScope {
  return scopeParam === 'all' ? 'all' : 'my'
}

export function specialistScopeToUrl(scope: SpecialistScope): string {
  return scope === 'my' ? 'my' : 'all'
}

export function parseSpecialistViewFromUrl(viewParam: string | null): SpecialistView {
  return viewParam === 'list' ? 'list' : 'kanban'
}

export function specialistViewToUrl(view: SpecialistView): string {
  return view === 'kanban' ? 'kanban' : 'list'
}

export function parseManagerSubsFromSearchParams(params: URLSearchParams): string[] {
  return parseRepeatedSearchParam(params, 'manager_sub')
}

export function parseSpecialistSubsFromSearchParams(params: URLSearchParams): string[] {
  return parseRepeatedSearchParam(params, 'specialist_sub')
}
