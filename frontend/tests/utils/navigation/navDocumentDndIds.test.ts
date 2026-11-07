import { describe, expect, it } from 'vitest'

import {
  DOC_DND_PREFIX,
  SECTION_DND_PREFIX,
  docDndId,
  parseDocDndId,
  parseSectionDndSlug,
  sectionDndId,
} from '@/utils/navigation/navDocumentDndIds'

describe('navDocumentDndIds', () => {
  it('собирает id документа и секции', () => {
    expect(docDndId('abc')).toBe(`${DOC_DND_PREFIX}abc`)
    expect(sectionDndId('outstaff')).toBe(`${SECTION_DND_PREFIX}outstaff`)
  })

  it('разбирает doc: и section:', () => {
    expect(parseDocDndId('doc:uuid-1')).toBe('uuid-1')
    expect(parseSectionDndSlug('section:hr')).toBe('hr')
  })

  it('принимает number через String()', () => {
    expect(parseDocDndId(42)).toBeNull()
    expect(parseSectionDndSlug(42)).toBeNull()
  })

  it('чужой префикс → null', () => {
    expect(parseDocDndId('section:hr')).toBeNull()
    expect(parseSectionDndSlug('doc:x')).toBeNull()
    expect(parseDocDndId('x')).toBeNull()
  })

  it('пустой remainder после префикса → пустая строка', () => {
    expect(parseDocDndId('doc:')).toBe('')
    expect(parseSectionDndSlug('section:')).toBe('')
  })

  it('двоеточие внутри id/slug остаётся хвостом, не вторым префиксом', () => {
    expect(parseDocDndId('doc:section:hr')).toBe('section:hr')
    expect(parseSectionDndSlug('section:doc:x')).toBe('doc:x')
  })
})
