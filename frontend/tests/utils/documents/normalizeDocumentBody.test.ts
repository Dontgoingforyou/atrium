import { describe, expect, it } from 'vitest'

import {
  documentBodyIsDirty,
  normalizeDocumentBody,
} from '@/utils/documents/normalizeDocumentBody'

describe('normalizeDocumentBody', () => {
  it('null / undefined / пустое → null', () => {
    expect(normalizeDocumentBody(null)).toBeNull()
    expect(normalizeDocumentBody(undefined)).toBeNull()
    expect(normalizeDocumentBody('')).toBeNull()
    expect(normalizeDocumentBody('   ')).toBeNull()
  })

  it('trim сохраняет содержимое', () => {
    expect(normalizeDocumentBody('  <p>x</p>  ')).toBe('<p>x</p>')
  })
})

describe('documentBodyIsDirty', () => {
  it('сравнивает нормализованные значения', () => {
    expect(documentBodyIsDirty('  <p>a</p>  ', '<p>a</p>')).toBe(false)
    expect(documentBodyIsDirty('<p>a</p>', '<p>b</p>')).toBe(true)
    expect(documentBodyIsDirty('', null)).toBe(false)
  })
})
