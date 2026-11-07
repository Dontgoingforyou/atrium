import { describe, expect, it } from 'vitest'

import type { ManagerSpecialistEntry } from '../../../src/types/specialist'
import {
  allManagersLabelForSpecialist,
  enrichEntriesWithAllManagers,
  filterBoardEntries,
} from '../../../src/domain/specialists/specialistCoManagers'

function entry(
  partial: Partial<ManagerSpecialistEntry> & Pick<ManagerSpecialistEntry, 'specialist_sub' | 'manager_sub'>,
): ManagerSpecialistEntry {
  return {
    id: partial.id ?? '1',
    specialist_sub: partial.specialist_sub,
    manager_sub: partial.manager_sub,
    manager_display_name: partial.manager_display_name ?? null,
    column_key: partial.column_key ?? 'new',
    position: partial.position ?? 0,
    version: partial.version ?? 1,
    display_name: partial.display_name ?? null,
    email: partial.email ?? null,
    avatar_url: partial.avatar_url ?? null,
    status_id: partial.status_id ?? null,
    status_title: partial.status_title ?? null,
    status_color: partial.status_color ?? null,
    created_at: partial.created_at ?? '2020-01-01T00:00:00Z',
  }
}

describe('allManagersLabelForSpecialist', () => {
  const directory = [
    entry({ specialist_sub: 's1', manager_sub: 'me', manager_display_name: 'Я' }),
    entry({ specialist_sub: 's1', manager_sub: 'm2', manager_display_name: 'Анна' }),
    entry({ specialist_sub: 's1', manager_sub: 'm3', manager_display_name: 'Борис' }),
  ]

  it('возвращает всех менеджеров, текущий первым', () => {
    expect(allManagersLabelForSpecialist('s1', directory, 'me')).toBe('Я, Анна, Борис')
  })

  it('один менеджер', () => {
    expect(allManagersLabelForSpecialist('s1', [directory[0]], 'me')).toBe('Я')
  })
})

describe('enrichEntriesWithAllManagers', () => {
  it('подставляет полный список менеджеров', () => {
    const directory = [
      entry({ specialist_sub: 's1', manager_sub: 'me', manager_display_name: 'Я' }),
      entry({ specialist_sub: 's1', manager_sub: 'm2', manager_display_name: 'Анна' }),
    ]
    const mine = [entry({ specialist_sub: 's1', manager_sub: 'me', manager_display_name: 'Я' })]
    const enriched = enrichEntriesWithAllManagers(mine, directory, 'me')
    expect(enriched[0].manager_display_name).toBe('Я, Анна')
  })
})

describe('filterBoardEntries', () => {
  const directory = [
    entry({ specialist_sub: 's1', manager_sub: 'me', status_id: 'st1' }),
    entry({ specialist_sub: 's1', manager_sub: 'm2', status_id: 'st2' }),
    entry({ specialist_sub: 's2', manager_sub: 'me', status_id: 'st1' }),
  ]

  it('в «мои» фильтрует по со-менеджеру из справочника', () => {
    const my = [directory[0], directory[2]]
    const filtered = filterBoardEntries(
      my,
      { managerSubs: ['m2'], specialistSubs: [] },
      directory,
      'my',
    )
    expect(filtered.map((e) => e.specialist_sub)).toEqual(['s1'])
  })

  it('фильтрует по выбранным specialist_sub', () => {
    const entries = [
      entry({
        specialist_sub: 's1',
        manager_sub: 'me',
        display_name: 'Board One',
      }),
      entry({
        specialist_sub: 's2',
        manager_sub: 'me',
        display_name: 'Board Two',
      }),
    ]
    const filtered = filterBoardEntries(
      entries,
      { managerSubs: [], specialistSubs: ['s1'] },
      entries,
      'my',
    )
    expect(filtered.map((e) => e.specialist_sub)).toEqual(['s1'])
  })

  it('пустой specialistSubs не отфильтровывает записи', () => {
    const entries = [
      entry({ specialist_sub: 's1', manager_sub: 'me', display_name: 'A' }),
    ]
    const filtered = filterBoardEntries(
      entries,
      { managerSubs: [], specialistSubs: [] },
      entries,
      'my',
    )
    expect(filtered).toHaveLength(1)
  })

  it('комбинирует фильтр менеджера и специалиста', () => {
    const filtered = filterBoardEntries(
      directory,
      { managerSubs: ['me'], specialistSubs: ['s2'] },
      directory,
      'all',
    )
    expect(filtered.map((e) => e.specialist_sub)).toEqual(['s2'])
  })
})
