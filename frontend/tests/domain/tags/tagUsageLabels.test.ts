import { describe, expect, it } from 'vitest'

import { tagUsageTaskLabel } from '../../../src/domain/tags/tagUsageLabels'

describe('tagUsageTaskLabel', () => {
  it('собирает номер и название', () => {
    expect(tagUsageTaskLabel({ number: 12, title: 'Сверка' })).toBe('#12 Сверка')
  })

  it('без номера оставляет только название', () => {
    expect(tagUsageTaskLabel({ number: null, title: 'Черновик' })).toBe('Черновик')
  })

  it('пустое название заменяет заглушкой', () => {
    expect(tagUsageTaskLabel({ number: 1, title: '  ' })).toBe('#1 Без названия')
  })
})
