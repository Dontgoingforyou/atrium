import { describe, expect, it } from 'vitest'
import { normalizePortalSearchResults, normalizeSearchHit } from '@/utils/search/normalizeSearchHit'

describe('normalizeSearchHit', () => {
  it('преобразует document', () => {
    const r = normalizeSearchHit({
      entity_type: 'document',
      document: {
        id: '550e8400-e29b-41d4-a716-446655440000',
        title: 'Заголовок',
        document_type: 'template',
        parent_document_id: null,
        author_sub: 'sub',
        author_email: null,
        owner_sub: null,
        owner_email: null,
        status: 'active',
        created_at: '2025-01-01T00:00:00Z',
        updated_at: '2025-01-01T00:00:00Z',
        tags: [],
        nav_node_slug: 'docs',
      },
    })
    expect(r.entity_type).toBe('document')
    expect(r.entity_id).toBe('550e8400-e29b-41d4-a716-446655440000')
    expect(r.title).toBe('Заголовок')
    expect(r.nav_node_slug).toBe('docs')
  })

  it('преобразует task', () => {
    const r = normalizeSearchHit({
      entity_type: 'task',
      task: {
        id: '770e8400-e29b-41d4-a716-446655440002',
        title: 'Задача',
        description_excerpt: 'Описание',
        status: 'todo',
        priority: 'medium',
        creator_sub: 'a',
        assignee_sub: null,
        created_at: '2025-01-01T00:00:00Z',
      },
    })
    expect(r.title).toBe('Задача')
    expect(r.snippet).toBe('Описание')
  })

  it('преобразует calendar_event', () => {
    const r = normalizeSearchHit({
      entity_type: 'calendar_event',
      calendar_event: {
        id: '880e8400-e29b-41d4-a716-446655440003',
        calendar_id: '990e8400-e29b-41d4-a716-446655440004',
        title: 'Стендап',
        starts_at: '2025-06-01T10:00:00Z',
        ends_at: '2025-06-01T10:30:00Z',
        calendar_title: 'Рабочий',
        location: 'Zoom',
      },
    })
    expect(r.entity_type).toBe('calendar_event')
    expect(r.entity_id).toBe('880e8400-e29b-41d4-a716-446655440003')
    expect(r.title).toBe('Стендап')
    expect(r.snippet).toBe('Рабочий · Zoom')
  })

  it('normalizePortalSearchResults обрабатывает массив', () => {
    const list = normalizePortalSearchResults([
      {
        entity_type: 'document',
        document: {
          id: '550e8400-e29b-41d4-a716-446655440000',
          title: 'X',
          document_type: 'template',
          parent_document_id: null,
          author_sub: 's',
          author_email: null,
          owner_sub: null,
          owner_email: null,
          status: 'active',
          created_at: '2025-01-01T00:00:00Z',
          updated_at: '2025-01-01T00:00:00Z',
          tags: [],
        },
      },
    ])
    expect(list).toHaveLength(1)
    expect(list[0].title).toBe('X')
  })

  it('normalizePortalSearchResults пропускает неизвестные типы без ошибки', () => {
    const list = normalizePortalSearchResults([
      { entity_type: 'agreement', agreement: { id: 'a', body_excerpt: 'x', status: 'draft', created_at: '2025-01-01T00:00:00Z' } },
      {
        entity_type: 'document',
        document: {
          id: '550e8400-e29b-41d4-a716-446655440000',
          title: 'OK',
          document_type: 'template',
          parent_document_id: null,
          author_sub: 's',
          author_email: null,
          owner_sub: null,
          owner_email: null,
          status: 'active',
          created_at: '2025-01-01T00:00:00Z',
          updated_at: '2025-01-01T00:00:00Z',
          tags: [],
        },
      },
    ])
    expect(list).toHaveLength(1)
    expect(list[0].title).toBe('OK')
  })

  it('не-объект и массив → ошибка (asRecord отбрасывает массив)', () => {
    expect(() => normalizeSearchHit(null)).toThrow('ожидался объект')
    expect(() => normalizeSearchHit([])).toThrow('ожидался объект')
  })

  it('normalizePortalSearchResults: не-массив → пустой список', () => {
    expect(normalizePortalSearchResults(null)).toEqual([])
    expect(normalizePortalSearchResults({})).toEqual([])
  })

  it('преобразует chat_message', () => {
    const r = normalizeSearchHit({
      entity_type: 'chat_message',
      chat: { id: 'chat-1', title: 'Общий' },
      message: { id: 'msg-1', body_excerpt: 'привет', created_at: '2025-01-01T00:00:00Z' },
    })
    expect(r.entity_type).toBe('chat_message')
    expect(r.entity_id).toBe('msg-1')
    expect(r.chat?.id).toBe('chat-1')
    expect(r.snippet).toBe('привет')
  })

  it('преобразует specialist', () => {
    const r = normalizeSearchHit({
      entity_type: 'specialist',
      specialist: { sub: 'sub-1', full_name: 'Иван', email: 'ivan@example.com' },
    })
    expect(r.entity_type).toBe('specialist')
    expect(r.entity_id).toBe('sub-1')
    expect(r.title).toBe('Иван')
    expect(r.snippet).toBe('ivan@example.com')
  })
})

