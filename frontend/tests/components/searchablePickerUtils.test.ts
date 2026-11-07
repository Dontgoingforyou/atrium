import { describe, expect, it } from 'vitest'

import {
  SEARCHABLE_PICKER_PAGE_SIZE,
  filterPickerOptions,
  labelByValue,
  paginateItems,
} from '@/components/common/searchablePickerUtils'

describe('filterPickerOptions', () => {
  const options = [
    { value: 'a', label: 'Анна', secondary: 'anna@ex.com' },
    { value: 'b', label: 'Борис', secondary: null },
    { value: 'dev-uuid', label: 'Вера' },
  ]

  it('исключает уже выбранные', () => {
    const out = filterPickerOptions(options, '', new Set(['a']))
    expect(out.map((o) => o.value)).toEqual(['b', 'dev-uuid'])
  })

  it('пустой запрос — все кроме excluded', () => {
    const out = filterPickerOptions(options, '   ', new Set())
    expect(out.map((o) => o.value)).toEqual(['a', 'b', 'dev-uuid'])
  })

  it('фильтрует по label', () => {
    const out = filterPickerOptions(options, 'бор', new Set())
    expect(out.map((o) => o.value)).toEqual(['b'])
  })

  it('фильтрует по secondary (email)', () => {
    const out = filterPickerOptions(options, 'anna@', new Set())
    expect(out.map((o) => o.value)).toEqual(['a'])
  })

  it('фильтрует по value', () => {
    const out = filterPickerOptions(options, 'dev-uuid', new Set())
    expect(out.map((o) => o.value)).toEqual(['dev-uuid'])
  })

  it('ничего не находит — пустой список', () => {
    expect(filterPickerOptions(options, 'zzz', new Set())).toEqual([])
  })

  it('размер страницы по умолчанию 15', () => {
    expect(SEARCHABLE_PICKER_PAGE_SIZE).toBe(15)
  })
})

describe('labelByValue', () => {
  const options = [
    { value: 'a', label: 'Анна' },
    { value: 'b', label: 'Борис' },
  ]

  it('возвращает label по value', () => {
    expect(labelByValue(options, 'b')).toBe('Борис')
  })

  it('неизвестный value — сам value (не падает)', () => {
    expect(labelByValue(options, 'missing')).toBe('missing')
  })
})

describe('paginateItems', () => {
  it('отрезает страницу и считает хвост', () => {
    expect(paginateItems(['a', 'b', 'c', 'd'], 2)).toEqual({
      visible: ['a', 'b'],
      remaining: 2,
    })
  })

  it('если элементов не больше лимита — хвоста нет', () => {
    expect(paginateItems(['a', 'b'], 15)).toEqual({
      visible: ['a', 'b'],
      remaining: 0,
    })
  })

  it('пустой список — пустая страница', () => {
    expect(paginateItems([], 15)).toEqual({ visible: [], remaining: 0 })
  })
})
