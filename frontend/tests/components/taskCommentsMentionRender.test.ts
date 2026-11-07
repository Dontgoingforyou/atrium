import { describe, expect, it } from 'vitest'
import {
  buildCommentBodySegments,
  buildMentionSegments,
  splitTextWithSafeUrls,
} from '../../src/components/tasks/taskCommentsMentionRender'
import type { PortalUser } from '../../src/types/chat'

const users: PortalUser[] = [
  { sub: 'u1', display_name: 'Test Outstaff', email: 't@e.com', username: 't' },
]

describe('buildMentionSegments', () => {
  it('подсвечивает полное имя с пробелом', () => {
    const body = 'Привет @Test Outstaff !'
    const segs = buildMentionSegments(body, ['u1'], users)
    const marks = segs.filter((s) => s.type === 'mark').map((s) => s.value)
    expect(marks).toEqual(['@Test Outstaff'])
  })

  it('legacy: @word без mentions', () => {
    const segs = buildMentionSegments('x @foo y', [], users)
    expect(segs).toEqual([
      { type: 'text', value: 'x ' },
      { type: 'mark', value: '@foo' },
      { type: 'text', value: ' y' },
    ])
  })
})

describe('splitTextWithSafeUrls', () => {
  it('выделяет https URL как link-сегмент', () => {
    const segs = splitTextWithSafeUrls(
      'см. https://docs.google.com/document/d/abc/edit?usp=sharing конец',
    )
    expect(segs).toEqual([
      { type: 'text', value: 'см. ' },
      {
        type: 'link',
        value: 'https://docs.google.com/document/d/abc/edit?usp=sharing',
      },
      { type: 'text', value: ' конец' },
    ])
  })

  it('не линкует javascript:, data: и ftp:', () => {
    expect(splitTextWithSafeUrls('click javascript:alert(1) here')).toEqual([
      { type: 'text', value: 'click javascript:alert(1) here' },
    ])
    expect(splitTextWithSafeUrls('x data:text/html,hi y')).toEqual([
      { type: 'text', value: 'x data:text/html,hi y' },
    ])
    expect(splitTextWithSafeUrls('см. ftp://files.example.com/a')).toEqual([
      { type: 'text', value: 'см. ftp://files.example.com/a' },
    ])
  })

  it('http:// тоже линкуется (не только https)', () => {
    expect(splitTextWithSafeUrls('см. http://example.com/a')).toEqual([
      { type: 'text', value: 'см. ' },
      { type: 'link', value: 'http://example.com/a' },
    ])
  })

  it('отбрасывает завершающую пунктуацию у URL', () => {
    expect(splitTextWithSafeUrls('открыть https://example.com.')).toEqual([
      { type: 'text', value: 'открыть ' },
      { type: 'link', value: 'https://example.com' },
      { type: 'text', value: '.' },
    ])
  })
})

describe('buildCommentBodySegments', () => {
  it('сохраняет mention рядом с URL', () => {
    const segs = buildCommentBodySegments(
      '@Test Outstaff смотри https://example.com/a ок',
      ['u1'],
      users,
    )
    expect(segs).toEqual([
      { type: 'mark', value: '@Test Outstaff' },
      { type: 'text', value: ' смотри ' },
      { type: 'link', value: 'https://example.com/a' },
      { type: 'text', value: ' ок' },
    ])
  })
})
