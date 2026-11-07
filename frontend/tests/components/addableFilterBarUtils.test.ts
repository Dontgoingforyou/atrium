import { describe, expect, it } from 'vitest'

import {
  ADDABLE_FILTER_EMPTY_PLACEHOLDER,
  addActiveFieldId,
  formatFilterChipSummary,
  initActiveFieldIds,
  removeActiveFieldId,
  shouldOpenPickerOnAdd,
  shouldShowAddFilterMenu,
  syncActiveFieldIds,
} from '../../src/components/common/addableFilterBarUtils'

describe('formatFilterChipSummary', () => {
  it('пустой выбор — плейсхолдер', () => {
    expect(formatFilterChipSummary('Статусы', [])).toBe(
      `Статусы: ${ADDABLE_FILTER_EMPTY_PLACEHOLDER}`,
    )
  })

  it('один выбранный — полное имя', () => {
    expect(formatFilterChipSummary('Теги', ['Backend'])).toBe('Теги: Backend')
  })

  it('несколько — первое имя и +N', () => {
    expect(formatFilterChipSummary('Исполнители', ['Анна', 'Борис', 'Вера'])).toBe(
      'Исполнители: Анна +2',
    )
  })
})

describe('initActiveFieldIds', () => {
  it('включает только поля с значениями', () => {
    expect(
      initActiveFieldIds([
        { id: 'status', hasValues: true },
        { id: 'tag', hasValues: false },
        { id: 'priority', hasValues: true },
      ]),
    ).toEqual(['status', 'priority'])
  })

  it('включает defaultActive без значений', () => {
    expect(
      initActiveFieldIds([
        { id: 'status', hasValues: false },
        { id: 'assignee', hasValues: false, defaultActive: true },
      ]),
    ).toEqual(['assignee'])
  })

  it('пустой список — пустой результат', () => {
    expect(initActiveFieldIds([])).toEqual([])
  })
})

describe('syncActiveFieldIds', () => {
  it('при появлении defaultActive добавляет чип', () => {
    expect(
      syncActiveFieldIds(
        ['status'],
        [
          { id: 'status', hasValues: false },
          { id: 'assignee', hasValues: false, defaultActive: true },
        ],
      ),
    ).toEqual(['status', 'assignee'])
  })

  it('убирает недоступные и сохраняет hasValues', () => {
    expect(
      syncActiveFieldIds(
        ['status', 'assignee'],
        [{ id: 'status', hasValues: true }],
      ),
    ).toEqual(['status'])
  })
})

describe('addActiveFieldId / removeActiveFieldId', () => {
  it('добавляет id, если его ещё нет', () => {
    expect(addActiveFieldId(['status'], 'tag')).toEqual(['status', 'tag'])
  })

  it('не дублирует уже активный id', () => {
    expect(addActiveFieldId(['status'], 'status')).toEqual(['status'])
  })

  it('удаляет id', () => {
    expect(removeActiveFieldId(['status', 'tag'], 'status')).toEqual(['tag'])
  })
})

describe('shouldOpenPickerOnAdd', () => {
  it('по умолчанию открывает пикер, если он есть', () => {
    expect(shouldOpenPickerOnAdd({ hasPicker: true })).toBe(true)
  })

  it('не открывает пикер у boolean-поля без renderPicker', () => {
    expect(shouldOpenPickerOnAdd({ hasPicker: false })).toBe(false)
    expect(shouldOpenPickerOnAdd({ hasPicker: false, openOnAdd: true })).toBe(false)
  })

  it('не открывает пикер при openOnAdd=false', () => {
    expect(shouldOpenPickerOnAdd({ hasPicker: true, openOnAdd: false })).toBe(false)
  })
})

describe('shouldShowAddFilterMenu', () => {
  it('скрывает «+ Добавить фильтр», когда неактивных полей нет', () => {
    expect(shouldShowAddFilterMenu(0)).toBe(false)
  })

  it('показывает меню, пока есть поля для добавления', () => {
    expect(shouldShowAddFilterMenu(1)).toBe(true)
    expect(shouldShowAddFilterMenu(3)).toBe(true)
  })
})
