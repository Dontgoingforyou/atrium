import { describe, expect, it } from 'vitest'

import {
  DEVELOPER_DOCS_ROOT_ID,
  DEVELOPER_DOCS_TITLE,
  GENERAL_DOCS_TITLE,
  NAV_SLUG_DEVELOPER_DOCS,
  NAV_SLUG_DOCUMENTS,
  isTopLevelForSectionMove,
  navDocHasBranch,
  parentDocumentIdForNavSlug,
} from '@/domain/documents/documentNavSections'
import type { NavDocBrief } from '@/types/portalNavigation'

describe('documentNavSections', () => {
  it('контракт UUID / slug / title совпадает с backend constants', () => {
    expect(DEVELOPER_DOCS_ROOT_ID).toBe('a1b2c3d4-e5f6-4a70-8b9c-0d1e2f3a4b5c')
    expect(NAV_SLUG_DOCUMENTS).toBe('__documents__')
    expect(NAV_SLUG_DEVELOPER_DOCS).toBe('__developer_docs__')
    expect(DEVELOPER_DOCS_TITLE).toBe('Документы для разработчиков')
    expect(GENERAL_DOCS_TITLE).toBe('Документы')
  })

  it('parentDocumentIdForNavSlug', () => {
    expect(parentDocumentIdForNavSlug(NAV_SLUG_DEVELOPER_DOCS)).toBe(DEVELOPER_DOCS_ROOT_ID)
    expect(parentDocumentIdForNavSlug(NAV_SLUG_DOCUMENTS)).toBeNull()
  })

  it('isTopLevelForSectionMove — только корни секций', () => {
    expect(isTopLevelForSectionMove(null)).toBe(true)
    expect(isTopLevelForSectionMove(undefined)).toBe(true)
    expect(isTopLevelForSectionMove(DEVELOPER_DOCS_ROOT_ID)).toBe(true)
    expect(isTopLevelForSectionMove('aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee')).toBe(false)
  })

  describe('navDocHasBranch', () => {
    it('false for leaf without shortcuts', () => {
      const doc: NavDocBrief = { id: '1', title: 'A' }
      expect(navDocHasBranch(doc)).toBe(false)
    })

    it('true when children present', () => {
      const doc: NavDocBrief = {
        id: '1',
        title: 'A',
        children: [{ id: '2', title: 'B' }],
      }
      expect(navDocHasBranch(doc)).toBe(true)
    })

    it('true when only shortcuts present', () => {
      const doc: NavDocBrief = {
        id: '1',
        title: 'A',
        shortcuts: [{ id: '3', title: 'Ярлык' }],
      }
      expect(navDocHasBranch(doc)).toBe(true)
    })
  })
})
