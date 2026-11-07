import { QueryClient } from '@tanstack/react-query'
import { describe, expect, it } from 'vitest'

import {
  patchAllSpecialistBoardCaches,
  restoreSpecialistBoardCaches,
  snapshotSpecialistBoardCaches,
  specialistBoardQueryKey,
  specialistBoardQueryKeys,
  withoutBoardAttachment,
} from '../../../src/domain/specialists/specialistBoardCache'
import type { ManagerSpecialistEntry } from '../../../src/types/specialist'

function entry(
  specialistSub: string,
  managerSub: string,
  managerName: string,
): ManagerSpecialistEntry {
  return {
    id: `${specialistSub}-${managerSub}`,
    specialist_sub: specialistSub,
    display_name: 'Pupkin',
    email: null,
    avatar_url: null,
    column_key: 'cv',
    position: 0,
    version: 1,
    manager_sub: managerSub,
    manager_display_name: managerName,
    status_id: null,
    status_title: null,
    status_color: null,
    created_at: '2026-01-01T00:00:00Z',
  }
}

describe('specialistBoardQueryKey(s)', () => {
  it('строит ключи my/all', () => {
    expect(specialistBoardQueryKey('my', 'u1')).toEqual([
      'portal',
      'specialists',
      'board',
      'my',
      'u1',
    ])
    expect(specialistBoardQueryKeys('u1')).toEqual([
      specialistBoardQueryKey('my', 'u1'),
      specialistBoardQueryKey('all', 'u1'),
    ])
  })
})

describe('withoutBoardAttachment', () => {
  it('убирает только закрепление указанного менеджера', () => {
    const rows = [entry('spec-1', 'alice', 'Alice'), entry('spec-1', 'mihail', 'Mihail')]
    const next = withoutBoardAttachment(rows, 'spec-1', 'mihail')
    expect(next).toHaveLength(1)
    expect(next[0]!.manager_sub).toBe('alice')
  })
})

describe('patch / snapshot / restore specialist board caches', () => {
  it('патчит оба scope и откатывает snapshot', () => {
    const qc = new QueryClient()
    const myKey = specialistBoardQueryKey('my', 'u1')
    const allKey = specialistBoardQueryKey('all', 'u1')
    const rows = [entry('s1', 'm1', 'M1'), entry('s1', 'm2', 'M2')]
    qc.setQueryData(myKey, rows)
    qc.setQueryData(allKey, rows)

    const snap = snapshotSpecialistBoardCaches(qc, 'u1')

    patchAllSpecialistBoardCaches(qc, 'u1', (prev) =>
      withoutBoardAttachment(prev, 's1', 'm2'),
    )
    expect(qc.getQueryData<ManagerSpecialistEntry[]>(myKey)).toHaveLength(1)
    expect(qc.getQueryData<ManagerSpecialistEntry[]>(allKey)).toHaveLength(1)

    restoreSpecialistBoardCaches(qc, snap)
    expect(qc.getQueryData<ManagerSpecialistEntry[]>(myKey)).toHaveLength(2)
    expect(qc.getQueryData<ManagerSpecialistEntry[]>(allKey)).toHaveLength(2)
  })

  it('не создаёт данные, если кэша не было', () => {
    const qc = new QueryClient()
    patchAllSpecialistBoardCaches(qc, 'u1', () => [entry('s', 'm', 'M')])
    expect(qc.getQueryData(specialistBoardQueryKey('my', 'u1'))).toBeUndefined()
  })
})
