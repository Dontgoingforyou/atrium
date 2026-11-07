// @vitest-environment jsdom

import { describe, expect, it } from 'vitest'

import {
  bodyToPlainPreview,
  formatDocumentHistoryValue,
  isDocumentCreatedAction,
  isTagIdsReplacedDiff,
} from '../../../src/domain/documents/documentHistoryFormatting'
import {
  DOCUMENT_ACTION_LABELS,
  DOCUMENT_STATUS_LABELS,
  TAG_IDS_REPLACED,
  UNTITLED_DOCUMENT_LABEL,
} from '../../../src/domain/documents/documentLabels'

const resolveUser = (sub: string) => (sub ? `U:${sub}` : '—')

describe('documentLabels', () => {
  it('статусы и сигнальное значение тегов — стабильные строки', () => {
    expect(DOCUMENT_STATUS_LABELS.draft).toBe('Черновик')
    expect(DOCUMENT_STATUS_LABELS.active).toBe('Опубликован')
    expect(DOCUMENT_STATUS_LABELS.archived).toBe('В архиве')
    expect(TAG_IDS_REPLACED).toBe('replaced')
    expect(UNTITLED_DOCUMENT_LABEL).toBe('Без названия')
  })

  it('событие created имеет лейбл', () => {
    expect(DOCUMENT_ACTION_LABELS.created).toBe('Документ создан')
  })
})

describe('bodyToPlainPreview', () => {
  it('извлекает textContent через DOMParser, не innerHTML', () => {
    expect(bodyToPlainPreview('<p>Привет, <b>мир</b></p>')).toBe('Привет, мир')
  })

  it('script не попадает в preview как разметка', () => {
    expect(bodyToPlainPreview('<script>alert(1)</script>Hi')).toBe('Hi')
    expect(bodyToPlainPreview('<script>alert(1)</script>Hi')).not.toContain('<script')
  })

  it('вырезает HTML-комментарии', () => {
    expect(bodyToPlainPreview('a<!-- comment -->b')).toBe('ab')
  })

  it('сжимает пробелы и возвращает — для пустого/только-тегов', () => {
    expect(bodyToPlainPreview('   ')).toBe('—')
    expect(bodyToPlainPreview('<p></p>')).toBe('—')
  })
})

describe('formatDocumentHistoryValue', () => {
  it('null/undefined → —', () => {
    expect(formatDocumentHistoryValue('title', null, resolveUser)).toBe('—')
    expect(formatDocumentHistoryValue('title', undefined, resolveUser)).toBe('—')
  })

  it('status → лейбл; неизвестный статус — как есть', () => {
    expect(formatDocumentHistoryValue('status', 'draft', resolveUser)).toBe('Черновик')
    expect(formatDocumentHistoryValue('status', 'unknown', resolveUser)).toBe('unknown')
  })

  it('owner_sub → resolveUserSub или —', () => {
    expect(formatDocumentHistoryValue('owner_sub', 'abc', resolveUser)).toBe('U:abc')
    expect(formatDocumentHistoryValue('owner_sub', '', resolveUser)).toBe('—')
  })

  it('parent_document_id → задано/не задано', () => {
    expect(formatDocumentHistoryValue('parent_document_id', null, resolveUser)).toBe('не задано')
    expect(formatDocumentHistoryValue('parent_document_id', '  ', resolveUser)).toBe('не задано')
    expect(formatDocumentHistoryValue('parent_document_id', 'id-1', resolveUser)).toBe('задано')
  })

  it('tag_ids → «обновлены» для сигнального replaced, иначе как есть', () => {
    expect(formatDocumentHistoryValue('tag_ids', TAG_IDS_REPLACED, resolveUser)).toBe('обновлены')
    expect(formatDocumentHistoryValue('tag_ids', '["t1"]', resolveUser)).toBe('["t1"]')
  })

  it('body → превью через DOMParser с обрезкой', () => {
    const html = `<p>${'a'.repeat(150)}</p>`
    const out = formatDocumentHistoryValue('body', html, resolveUser)
    expect(out.endsWith('…')).toBe(true)
    expect(out.length).toBeLessThanOrEqual(121)
  })

  it('body пустой → —', () => {
    expect(formatDocumentHistoryValue('body', '   ', resolveUser)).toBe('—')
    expect(formatDocumentHistoryValue('body', '<p></p>', resolveUser)).toBe('—')
  })

  it('action → лейбл события или ключ', () => {
    expect(formatDocumentHistoryValue('action', 'created', resolveUser)).toBe('Документ создан')
    expect(formatDocumentHistoryValue('action', 'updated', resolveUser)).toBe('updated')
  })

  it('произвольное поле → строка как есть', () => {
    expect(formatDocumentHistoryValue('title', 'Мой документ', resolveUser)).toBe('Мой документ')
    expect(formatDocumentHistoryValue('icon_emoji', '📄', resolveUser)).toBe('📄')
  })
})

describe('isTagIdsReplacedDiff / isDocumentCreatedAction', () => {
  it('tag_ids replaced только когда old=new=replaced', () => {
    expect(isTagIdsReplacedDiff({ old: TAG_IDS_REPLACED, new: TAG_IDS_REPLACED })).toBe(true)
    expect(isTagIdsReplacedDiff({ old: TAG_IDS_REPLACED, new: 'x' })).toBe(false)
    expect(isTagIdsReplacedDiff({ old: null, new: TAG_IDS_REPLACED })).toBe(false)
  })

  it('document created action — по new === created', () => {
    expect(isDocumentCreatedAction({ old: null, new: 'created' })).toBe(true)
    expect(isDocumentCreatedAction({ old: 'created', new: 'updated' })).toBe(false)
  })
})
