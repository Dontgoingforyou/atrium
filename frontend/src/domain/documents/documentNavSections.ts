import type { NavDocBrief } from '../../types/portalNavigation'

export const DEVELOPER_DOCS_ROOT_ID = 'a1b2c3d4-e5f6-4a70-8b9c-0d1e2f3a4b5c'
export const DEVELOPER_DOCS_TITLE = 'Документы для разработчиков'
export const GENERAL_DOCS_TITLE = 'Документы'
export const NAV_SLUG_DOCUMENTS = '__documents__'
export const NAV_SLUG_DEVELOPER_DOCS = '__developer_docs__'

export function parentDocumentIdForNavSlug(slug: string): string | null {
  if (slug === NAV_SLUG_DEVELOPER_DOCS) return DEVELOPER_DOCS_ROOT_ID
  return null
}

export function isTopLevelForSectionMove(parentDocumentId: string | null | undefined): boolean {
  return parentDocumentId == null || parentDocumentId === DEVELOPER_DOCS_ROOT_ID
}

export function navDocHasBranch(doc: NavDocBrief): boolean {
  return (doc.children?.length ?? 0) > 0 || (doc.shortcuts?.length ?? 0) > 0
}
