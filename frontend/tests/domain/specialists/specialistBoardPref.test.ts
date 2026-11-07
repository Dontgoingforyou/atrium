import { describe, expect, it } from 'vitest'

import {
  buildSpecialistColumnSelectOptions,
  computeSpecialistKanbanDisplay,
  findOwnBoardEntry,
  groupKanbanEntriesBySpecialist,
  hiddenColumnKeysAfterSelect,
  mergeSpecialistColumnOrder,
} from '../../../src/domain/specialists/specialistBoardPref'
import { KANBAN_OTHER_BUCKET } from '../../../src/domain/kanban/kanbanDisplayCommon'
import type { ManagerSpecialistEntry, SpecialistColumn } from '../../../src/types/specialist'

const columns: SpecialistColumn[] = [
  { id: '1', key: 'active', title: 'Активные', color: '#111', position: 0 },
  { id: '2', key: 'bench', title: 'Бенч', color: '#222', position: 1 },
  { id: '3', key: 'archive', title: 'Архив', color: '#333', position: 2 },
]

function entry(
  partial: Pick<
    ManagerSpecialistEntry,
    'id' | 'specialist_sub' | 'column_key' | 'position'
  > &
    Partial<ManagerSpecialistEntry>,
): ManagerSpecialistEntry {
  return {
    display_name: partial.display_name ?? partial.specialist_sub,
    email: null,
    avatar_url: null,
    manager_sub: 'mgr',
    manager_display_name: partial.manager_display_name ?? null,
    status_id: partial.status_id ?? null,
    status_title: partial.status_title ?? null,
    status_color: partial.status_color ?? null,
    created_at: '',
    version: 1,
    ...partial,
  }
}

describe('buildSpecialistColumnSelectOptions', () => {
  it('включает скрытую на канбане колонку', () => {
    const values = buildSpecialistColumnSelectOptions(columns, 'active').map((o) => o.value)
    expect(values).toEqual(['active', 'bench', 'archive'])
  })

  it('добавляет текущий ключ, если его нет в справочнике', () => {
    const values = buildSpecialistColumnSelectOptions(columns, 'peredat-vo-vne').map((o) => o.value)
    expect(values).toContain('peredat-vo-vne')
  })
})

describe('hiddenColumnKeysAfterSelect', () => {
  it('убирает выбранную скрытую колонку, остальные оставляет', () => {
    expect(hiddenColumnKeysAfterSelect(['archive', 'peredat-vo-vne'], 'peredat-vo-vne')).toEqual([
      'archive',
    ])
  })
})

describe('findOwnBoardEntry', () => {
  it('находит только закрепление текущего менеджера', () => {
    const rows = [
      entry({ id: 'a', specialist_sub: 'kuz', column_key: 'new', position: 0, manager_sub: 'other' }),
      entry({ id: 'b', specialist_sub: 'kuz', column_key: 'new', position: 1, manager_sub: 'me' }),
    ]
    expect(findOwnBoardEntry(rows, 'kuz', 'me')?.id).toBe('b')
    expect(findOwnBoardEntry(rows, 'kuz', 'nobody')).toBeUndefined()
  })
})

describe('mergeSpecialistColumnOrder', () => {
  it('без pref — порядок по position колонок', () => {
    expect(mergeSpecialistColumnOrder(columns, null)).toEqual(['active', 'bench', 'archive'])
  })

  it('сохраняет pref.column_order и дописывает недостающие', () => {
    expect(
      mergeSpecialistColumnOrder(columns, {
        column_order: ['archive', 'active'],
        hidden_column_keys: [],
      }),
    ).toEqual(['archive', 'active', 'bench'])
  })
})

describe('computeSpecialistKanbanDisplay', () => {
  const order = ['active', 'bench', 'archive']

  it('добавляет «Прочие» при скрытой колонке с карточками', () => {
    const entries = [entry({ id: 'e1', specialist_sub: 's1', column_key: 'archive', position: 0 })]
    const pref = { column_order: order, hidden_column_keys: ['archive'] }
    const d = computeSpecialistKanbanDisplay(order, entries, pref, false)
    expect(d.displayColumnKeys[d.displayColumnKeys.length - 1]).toBe(KANBAN_OTHER_BUCKET)
    expect(d.entriesForColumn(KANBAN_OTHER_BUCKET).map((e) => e.id)).toEqual(['e1'])
  })

  it('при «Показать скрытые» не использует агрегатор', () => {
    const entries = [entry({ id: 'e1', specialist_sub: 's1', column_key: 'archive', position: 0 })]
    const pref = { column_order: order, hidden_column_keys: ['archive'] }
    const d = computeSpecialistKanbanDisplay(order, entries, pref, true)
    expect(d.displayColumnKeys).not.toContain(KANBAN_OTHER_BUCKET)
    expect(d.entriesForColumn('archive').map((e) => e.id)).toEqual(['e1'])
  })

  it('сортирует карточки колонки по position', () => {
    const entries = [
      entry({ id: 'e2', specialist_sub: 's2', column_key: 'active', position: 2 }),
      entry({ id: 'e1', specialist_sub: 's1', column_key: 'active', position: 1 }),
    ]
    const d = computeSpecialistKanbanDisplay(order, entries, null, false)
    expect(d.entriesForColumn('active').map((e) => e.id)).toEqual(['e1', 'e2'])
  })
})

describe('groupKanbanEntriesBySpecialist', () => {
  it('одна карточка на specialist_sub, объединяет менеджеров и берёт статус', () => {
    const grouped = groupKanbanEntriesBySpecialist([
      entry({
        id: 'a',
        specialist_sub: 's1',
        column_key: 'active',
        position: 2,
        manager_display_name: 'Иванов',
        status_id: null,
      }),
      entry({
        id: 'b',
        specialist_sub: 's1',
        column_key: 'active',
        position: 1,
        manager_display_name: 'Петров',
        status_id: 'st1',
        status_title: 'В работе',
        status_color: '#0f0',
      }),
    ])
    expect(grouped).toHaveLength(1)
    expect(grouped[0]!.id).toBe('b')
    expect(grouped[0]!.status_id).toBe('st1')
    expect(grouped[0]!.manager_display_name).toBe('Петров, Иванов')
  })

  it('предпочитает закрепление текущего менеджера как primary', () => {
    const grouped = groupKanbanEntriesBySpecialist(
      [
        entry({
          id: 'a',
          specialist_sub: 's1',
          column_key: 'active',
          position: 1,
          manager_sub: 'other',
          manager_display_name: 'Другой',
        }),
        entry({
          id: 'b',
          specialist_sub: 's1',
          column_key: 'active',
          position: 2,
          manager_sub: 'me',
          manager_display_name: 'Я',
        }),
      ],
      'me',
    )
    expect(grouped).toHaveLength(1)
    expect(grouped[0]!.id).toBe('b')
    expect(grouped[0]!.manager_sub).toBe('me')
    expect(grouped[0]!.manager_display_name).toBe('Другой, Я')
  })
})
