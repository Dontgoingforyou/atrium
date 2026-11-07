import { describe, expect, it } from 'vitest'

import {
  DOCUMENT_TAGS_EDITOR_ATTR,
  DOCUMENT_TAGS_EDITOR_SELECTOR,
} from '@/domain/documents/documentTagsEditor'

describe('documentTagsEditor', () => {
  it('селектор строится из data-атрибута редактора тегов', () => {
    expect(DOCUMENT_TAGS_EDITOR_ATTR).toBe('data-document-tags-editor')
    expect(DOCUMENT_TAGS_EDITOR_SELECTOR).toBe('[data-document-tags-editor]')
  })
})
