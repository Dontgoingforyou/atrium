// @vitest-environment jsdom

import { describe, expect, it } from 'vitest'

import {
  SEARCH_HIGHLIGHT_ATTR,
  SEARCH_HIGHLIGHT_PARAM,
  SEARCH_HIGHLIGHT_QUERY_MAX_LEN,
  clampHighlightQuery,
  highlightExactPlainTextParts,
  highlightInSanitizedHtml,
  highlightPlainTextParts,
  plainTextHasHighlight,
  tokenizeHighlightQuery,
} from '@/utils/search/searchHighlight'

describe('clampHighlightQuery', () => {
  it('пустая и пробелы — null', () => {
    expect(clampHighlightQuery(null)).toBeNull()
    expect(clampHighlightQuery('')).toBeNull()
    expect(clampHighlightQuery('   ')).toBeNull()
  })

  it('обрезает слишком длинную строку', () => {
    const long = 'a'.repeat(SEARCH_HIGHLIGHT_QUERY_MAX_LEN + 20)
    const out = clampHighlightQuery(long)
    expect(out).toHaveLength(SEARCH_HIGHLIGHT_QUERY_MAX_LEN)
  })

  it('возвращает trim', () => {
    expect(clampHighlightQuery('  hello  ')).toBe('hello')
  })
})

describe('tokenizeHighlightQuery', () => {
  it('по умолчанию оставляет токены от 2 символов, включая предлоги', () => {
    expect(tokenizeHighlightQuery('a ab abc')).toEqual(['ab', 'abc'])
    expect(tokenizeHighlightQuery('найти специалиста на бенч')).toEqual([
      'найти',
      'специалиста',
      'на',
      'бенч',
    ])
  })

  it('в семантическом режиме отбрасывает предлоги и токены короче 3', () => {
    expect(tokenizeHighlightQuery('a ab abc', { dropServiceTokens: true })).toEqual(['abc'])
    expect(tokenizeHighlightQuery('найти специалиста на бенч', { dropServiceTokens: true })).toEqual([
      'найти',
      'специалиста',
      'бенч',
    ])
  })

  it('дедуплицирует без учёта регистра', () => {
    expect(tokenizeHighlightQuery('Test test TEST')).toEqual(['Test'])
  })

  it('пустой query — пустой список', () => {
    expect(tokenizeHighlightQuery('')).toEqual([])
    expect(tokenizeHighlightQuery(' a ')).toEqual([])
  })
})

describe('highlightPlainTextParts', () => {
  it('без токенов — один plain-фрагмент', () => {
    expect(highlightPlainTextParts('привет мир', '')).toEqual([{ type: 'text', value: 'привет мир' }])
  })

  it('подсвечивает совпадение case-insensitive', () => {
    expect(highlightPlainTextParts('Hello WORLD', 'world')).toEqual([
      { type: 'text', value: 'Hello ' },
      { type: 'mark', value: 'WORLD' },
    ])
  })

  it('несколько вхождений', () => {
    const parts = highlightPlainTextParts('foo bar foo', 'foo')
    expect(parts.filter((p) => p.type === 'mark').map((p) => p.value)).toEqual(['foo', 'foo'])
  })

  it('семантический режим не красит предлог «на»', () => {
    const parts = highlightPlainTextParts('работа на бенч', 'найти на бенч', {
      dropServiceTokens: true,
    })
    expect(parts.filter((p) => p.type === 'mark').map((p) => p.value)).toEqual(['бенч'])
  })

  it('regex-метасимволы в query — литеральный матч', () => {
    expect(highlightPlainTextParts('foo (bar)', '(bar)')).toEqual([
      { type: 'text', value: 'foo ' },
      { type: 'mark', value: '(bar)' },
    ])
  })
})

describe('highlightExactPlainTextParts', () => {
  it('подсвечивает непрерывный фрагмент целиком', () => {
    expect(
      highlightExactPlainTextParts('Правый клик — ответ, реакция', 'клик — ответ'),
    ).toEqual([
      { type: 'text', value: 'Правый ' },
      { type: 'mark', value: 'клик — ответ' },
      { type: 'text', value: ', реакция' },
    ])
  })

  it('без совпадения — весь текст plain', () => {
    expect(highlightExactPlainTextParts('привет', 'чужой')).toEqual([
      { type: 'text', value: 'привет' },
    ])
  })
})

describe('highlightInSanitizedHtml', () => {
  it('пустой query — исходный html', () => {
    const html = '<p>Текст</p>'
    expect(highlightInSanitizedHtml(html, '')).toBe(html)
  })

  it('оборачивает текст внутри тегов, не ломая разметку', () => {
    const html = '<p>Статус <strong>в работе</strong></p>'
    const out = highlightInSanitizedHtml(html, 'работе')
    expect(out).toContain(`<mark ${SEARCH_HIGHLIGHT_ATTR}="1">работе</mark>`)
    expect(out).toContain('<strong>')
    expect(out).not.toContain('<strong><mark')
  })

  it('не подсвечивает внутри атрибутов', () => {
    const html = '<a href="/documents/abc-работе">ссылка</a>'
    const out = highlightInSanitizedHtml(html, 'работе')
    expect(out).toContain('href="/documents/abc-работе"')
    expect(out).not.toMatch(/href="[^"]*<mark/)
  })

  it('XSS в query не создаёт теги — только текстовый матч', () => {
    const html = '<p>hello &lt;script&gt;</p>'
    const out = highlightInSanitizedHtml(html, '<script>')
    expect(out.toLowerCase()).not.toContain('<script>')
    expect(out).toContain(SEARCH_HIGHLIGHT_ATTR)
  })

  it('не подсвечивает текст внутри script/style', () => {
    const html =
      '<script>secret token</script><style>.token { color: red }</style><p>visible token</p>'
    const out = highlightInSanitizedHtml(html, 'token')
    expect(out).not.toMatch(/<mark[^>]*>[^<]*secret/i)
    expect(out).toContain(`<mark ${SEARCH_HIGHLIGHT_ATTR}="1">token</mark>`)
  })
})

describe('plainTextHasHighlight', () => {
  it('true при совпадении токена, false без токенов или без текста', () => {
    expect(plainTextHasHighlight('Hello WORLD', 'world')).toBe(true)
    expect(plainTextHasHighlight('привет', 'чужой')).toBe(false)
    expect(plainTextHasHighlight('привет', '')).toBe(false)
    expect(plainTextHasHighlight('', 'ab')).toBe(false)
  })
})

describe('constants', () => {
  it('имя query-параметра highlight', () => {
    expect(SEARCH_HIGHLIGHT_PARAM).toBe('highlight')
  })
})

