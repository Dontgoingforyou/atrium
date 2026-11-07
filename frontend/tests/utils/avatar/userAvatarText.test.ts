import { describe, expect, it } from 'vitest'

import { initialsFromLabel } from '@/utils/avatar/userAvatarText'

describe('initialsFromLabel', () => {
  it('пусто → ?', () => {
    expect(initialsFromLabel('')).toBe('?')
    expect(initialsFromLabel('   ')).toBe('?')
  })

  it('два слова → инициалы', () => {
    expect(initialsFromLabel('Иван Петров')).toBe('ИП')
  })

  it('одно длинное слово → первые 2 символа', () => {
    expect(initialsFromLabel('admin')).toBe('AD')
  })

  it('один символ', () => {
    expect(initialsFromLabel('я')).toBe('Я')
  })
})
