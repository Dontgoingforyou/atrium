import { describe, expect, it } from 'vitest'

import { normalizePortalSemanticResults, normalizeSemanticHit } from '@/utils/search/normalizeSemanticHit'

describe('normalizeSemanticHit', () => {
  it('maps document hit with excerpt title', () => {
    const r = normalizeSemanticHit({
      entity_type: 'document',
      entity_id: 'doc-1',
      text_excerpt: 'Заголовок документа\n\nТело',
      similarity_score: 0.87,
      meta: { author_sub: 'u1' },
    })
    expect(r.entity_type).toBe('document')
    expect(r.entity_id).toBe('doc-1')
    expect(r.title).toContain('Заголовок')
    expect(r.similarity_score).toBe(0.87)
  })

  it('maps chat_message with chat_id in meta', () => {
    const r = normalizeSemanticHit({
      entity_type: 'chat_message',
      entity_id: 'msg-1',
      text_excerpt: 'текст сообщения',
      similarity_score: 0.5,
      meta: { chat_id: 'chat-1', author_sub: 'u1' },
    })
    expect(r.chat?.id).toBe('chat-1')
    expect(r.message?.id).toBe('msg-1')
  })

  it('maps specialist_note with specialist_sub', () => {
    const r = normalizeSemanticHit({
      entity_type: 'specialist_note',
      entity_id: 'note-1',
      text_excerpt: 'важная заметка',
      similarity_score: 0.6,
      meta: { specialist_sub: 'sub-abc', author_sub: 'mgr' },
    })
    expect(r.specialist_sub).toBe('sub-abc')
  })

  it('maps calendar_event', () => {
    const r = normalizeSemanticHit({
      entity_type: 'calendar_event',
      entity_id: 'ev-1',
      text_excerpt: 'Стендап\n\nZoom',
      similarity_score: 0.7,
      meta: { calendar_id: 'cal-1' },
    })
    expect(r.entity_type).toBe('calendar_event')
    expect(r.title).toContain('Стендап')
  })

  it('maps agreement with excerpt title', () => {
    const r = normalizeSemanticHit({
      entity_type: 'agreement',
      entity_id: 'agr-1',
      text_excerpt: 'Договорённость о сроках\n\nдетали',
      similarity_score: 0.42,
      meta: { created_by_sub: 'u1', status: 'draft' },
    })
    expect(r.entity_type).toBe('agreement')
    expect(r.entity_id).toBe('agr-1')
    expect(r.title).toContain('Договорённость')
  })

  it('не-объект → ошибка', () => {
    expect(() => normalizeSemanticHit(null)).toThrow('ожидался объект')
    expect(() => normalizeSemanticHit([])).toThrow('ожидался объект')
  })

  it('NaN и Infinity у similarity_score → null', () => {
    const nanHit = normalizeSemanticHit({
      entity_type: 'document',
      entity_id: 'doc-1',
      text_excerpt: 'x',
      similarity_score: Number.NaN,
    })
    const infHit = normalizeSemanticHit({
      entity_type: 'document',
      entity_id: 'doc-1',
      text_excerpt: 'x',
      similarity_score: Number.POSITIVE_INFINITY,
    })
    expect(nanHit.similarity_score).toBeNull()
    expect(infHit.similarity_score).toBeNull()
  })

  it('normalizePortalSemanticResults пропускает битые элементы', () => {
    const list = normalizePortalSemanticResults({
      results: [
        { entity_type: 'unknown_type', entity_id: 'x', text_excerpt: 'bad' },
        { entity_type: 'document', entity_id: 'ok', text_excerpt: 'Заголовок', similarity_score: 0.5 },
      ],
    })
    expect(list).toHaveLength(1)
    expect(list[0]?.entity_id).toBe('ok')
  })
})
