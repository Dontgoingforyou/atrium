// @vitest-environment jsdom

import { describe, expect, it } from 'vitest'

import { formatHistoryValue, truncateHistoryText } from '../../../src/domain/tasks/taskHistoryFormatting'

const resolveUser = (sub: string | null | undefined) => (sub ? `U:${sub}` : '—')
const resolvers = {
  documentTitle: (id: string) => `Doc:${id}`,
  chatTitle: (id: string) => `Chat:${id}`,
}

describe('truncateHistoryText', () => {
  it('сжимает пробелы и не режет короткие строки', () => {
    expect(truncateHistoryText('  a   b  ')).toBe('a b')
  })

  it('обрезает длинный текст с многоточием', () => {
    const long = 'x'.repeat(130)
    expect(truncateHistoryText(long, 10)).toBe(`${'x'.repeat(10)}…`)
  })
})

describe('formatHistoryValue', () => {
  it('null/undefined → —', () => {
    expect(formatHistoryValue('title', null, resolveUser, resolvers)).toBe('—')
    expect(formatHistoryValue('title', undefined, resolveUser, resolvers)).toBe('—')
  })

  it('assignee_sub и assignee_subs', () => {
    expect(formatHistoryValue('assignee_sub', 'alice', resolveUser, resolvers)).toBe('U:alice')
    expect(formatHistoryValue('assignee_sub', '', resolveUser, resolvers)).toBe('—')
    expect(formatHistoryValue('assignee_subs', ['a', 'b'], resolveUser, resolvers)).toBe(
      'U:a, U:b',
    )
    expect(formatHistoryValue('assignee_subs', 'a, b', resolveUser, resolvers)).toBe('U:a, U:b')
    expect(formatHistoryValue('assignee_subs', [], resolveUser, resolvers)).toBe('—')
  })

  it('description: strip HTML и truncate', () => {
    expect(
      formatHistoryValue('description', '<p>Привет <b>мир</b></p>', resolveUser, resolvers),
    ).toBe('Привет мир')
  })

  it('description: script не остаётся в тексте', () => {
    expect(
      formatHistoryValue('description', '<script>alert(1)</script>Hi', resolveUser, resolvers),
    ).toBe('Hi')
  })

  it('assignee_subs с пустыми элементами игнорирует их', () => {
    expect(formatHistoryValue('assignee_subs', ['a', '', 'b'], resolveUser, resolvers)).toBe(
      'U:a, U:b',
    )
  })

  it('status и priority через лейблы', () => {
    expect(formatHistoryValue('status', 'done', resolveUser, resolvers)).toBe('Завершена')
    expect(formatHistoryValue('priority', 'high', resolveUser, resolvers)).toBe('Высокий')
  })

  it('due_at форматирует дату или —', () => {
    expect(formatHistoryValue('due_at', null, resolveUser, resolvers)).toBe('—')
    const formatted = formatHistoryValue('due_at', '2026-03-15T12:00:00Z', resolveUser, resolvers)
    expect(formatted).toMatch(/\d/)
    expect(formatted).not.toBe('—')
  })

  it('action created → Создание задачи', () => {
    expect(formatHistoryValue('action', 'created', resolveUser, resolvers)).toBe('Создание задачи')
    expect(formatHistoryValue('action', 'updated', resolveUser, resolvers)).toBe('updated')
  })

  it('document_id и chat_id через resolvers', () => {
    expect(formatHistoryValue('document_id', 'd1', resolveUser, resolvers)).toBe('Doc:d1')
    expect(formatHistoryValue('chat_id', 'c1', resolveUser, resolvers)).toBe('Chat:c1')
    expect(formatHistoryValue('document_id', null, resolveUser, resolvers)).toBe('—')
  })

  it('прочее поле → String(v)', () => {
    expect(formatHistoryValue('title', 'Hello', resolveUser, resolvers)).toBe('Hello')
  })
})
