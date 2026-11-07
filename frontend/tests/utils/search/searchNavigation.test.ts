import { describe, expect, it } from 'vitest'

import type { SearchResult } from '@/types/search'
import { SEARCH_HIGHLIGHT_QUERY_MAX_LEN } from '@/utils/search/searchHighlight'
import { getSearchResultHref } from '@/utils/search/searchNavigation'

function hit(partial: Partial<SearchResult> & Pick<SearchResult, 'entity_type' | 'entity_id'>): SearchResult {
  return {
    title: null,
    snippet: null,
    created_at: null,
    nav_node_slug: null,
    ...partial,
  }
}

describe('getSearchResultHref', () => {
  it('документ со slug — /p/{slug}/documents/{id}', () => {
    expect(getSearchResultHref(hit({ entity_type: 'document', entity_id: 'doc-uuid', nav_node_slug: 'section-a' }))).toBe(
      '/p/section-a/documents/doc-uuid',
    )
  })

  it('документ без slug — /documents/{id}', () => {
    expect(getSearchResultHref(hit({ entity_type: 'document', entity_id: 'doc-uuid' }))).toBe('/documents/doc-uuid')
  })

  it('пустой slug даёт путь без /p/', () => {
    expect(getSearchResultHref(hit({ entity_type: 'document', entity_id: 'doc-uuid', nav_node_slug: '' }))).toBe(
      '/documents/doc-uuid',
    )
  })

  it('кодирует id и slug с / и ../ (не open redirect)', () => {
    const id = '../evil/path'
    const slug = 'a/../b'
    const href = getSearchResultHref(hit({ entity_type: 'document', entity_id: id, nav_node_slug: slug }))
    expect(href).toBe(`/p/${encodeURIComponent(slug)}/documents/${encodeURIComponent(id)}`)
    expect(href).not.toContain('../')
  })

  it('chat_message открывает чат с query chat и message', () => {
    const chatId = '550e8400-e29b-41d4-a716-446655440001'
    const msgId = '660e8400-e29b-41d4-a716-446655440002'
    expect(
      getSearchResultHref(
        hit({
          entity_type: 'chat_message',
          entity_id: msgId,
          snippet: 'hi',
          chat: { id: chatId, title: null },
          message: { id: msgId, body: 'hi' },
        }),
      ),
    ).toBe(`/chats?chat=${encodeURIComponent(chatId)}&message=${encodeURIComponent(msgId)}`)
  })

  it('chat_message без chat → /chats', () => {
    expect(getSearchResultHref(hit({ entity_type: 'chat_message', entity_id: 'msg-1' }))).toBe('/chats')
  })

  it('learning_material → / (раздел обучения заморожен)', () => {
    expect(getSearchResultHref(hit({ entity_type: 'learning_material', entity_id: 'mat-1', title: 'Курс' }))).toBe('/')
  })

  it('agreement → / (нет экрана в поиске)', () => {
    expect(getSearchResultHref(hit({ entity_type: 'agreement', entity_id: 'agr-1' }))).toBe('/')
  })

  it('specialist_note со specialist_sub — профиль специалиста', () => {
    expect(
      getSearchResultHref(hit({ entity_type: 'specialist_note', entity_id: 'note-1', specialist_sub: 'sub-xyz' })),
    ).toBe('/specialists?sub=sub-xyz')
  })

  it('specialist_note без specialist_sub → /specialists', () => {
    expect(getSearchResultHref(hit({ entity_type: 'specialist_note', entity_id: 'note-1' }))).toBe('/specialists')
  })

  it('добавляет highlight к href документа', () => {
    expect(
      getSearchResultHref(hit({ entity_type: 'document', entity_id: 'doc-uuid', nav_node_slug: 'section-a' }), {
        highlightQuery: 'регламент',
      }),
    ).toBe('/p/section-a/documents/doc-uuid?highlight=%D1%80%D0%B5%D0%B3%D0%BB%D0%B0%D0%BC%D0%B5%D0%BD%D1%82')
  })

  it('добавляет highlight к href сообщения чата', () => {
    const chatId = '550e8400-e29b-41d4-a716-446655440001'
    const msgId = '660e8400-e29b-41d4-a716-446655440002'
    expect(
      getSearchResultHref(
        hit({
          entity_type: 'chat_message',
          entity_id: msgId,
          snippet: 'hi',
          chat: { id: chatId, title: null },
          message: { id: msgId, body: 'hi' },
        }),
        { highlightQuery: 'hi' },
      ),
    ).toBe(`/chats?chat=${encodeURIComponent(chatId)}&message=${encodeURIComponent(msgId)}&highlight=hi`)
  })

  it('пустой highlight не добавляет query', () => {
    expect(getSearchResultHref(hit({ entity_type: 'task', entity_id: 'task-1' }), { highlightQuery: '  ' })).toBe(
      '/tasks/task-1',
    )
  })

  it('highlight в href обрезается до SEARCH_HIGHLIGHT_QUERY_MAX_LEN', () => {
    const long = 'а'.repeat(SEARCH_HIGHLIGHT_QUERY_MAX_LEN + 50)
    const href = getSearchResultHref(hit({ entity_type: 'document', entity_id: 'd1' }), {
      highlightQuery: long,
    })
    const q = new URL(href, 'https://portal.test').searchParams.get('highlight')
    expect(q).toHaveLength(SEARCH_HIGHLIGHT_QUERY_MAX_LEN)
  })

  it('task id с ../ кодируется', () => {
    expect(getSearchResultHref(hit({ entity_type: 'task', entity_id: '../evil' }))).toBe(
      `/tasks/${encodeURIComponent('../evil')}`,
    )
  })

  it('calendar_event → /calendar?event=', () => {
    expect(getSearchResultHref(hit({ entity_type: 'calendar_event', entity_id: 'ev-99', title: 'Митинг' }))).toBe(
      '/calendar?event=ev-99',
    )
  })
})
