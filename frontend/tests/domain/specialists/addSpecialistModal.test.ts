import { describe, expect, it } from 'vitest'

import { listAddSpecialistModalRows } from '../../../src/domain/specialists/addSpecialistModal'

const onBoard = {
  sub: 'alina',
  display_name: 'Alina Example',
  email: 'alina.example@example.com',
  username: 'aexample',
}

const notOnBoard = {
  sub: 'boris',
  display_name: 'Boris Example',
  email: 'specialist.one@example.com',
  username: 'bexample',
}

describe('listAddSpecialistModalRows', () => {
  it('уже на доске не скрывает: поиск al даёт его с действием перенести', () => {
    const rows = listAddSpecialistModalRows([onBoard, notOnBoard], new Set(['alina']), 'al')
    expect(rows.map((row) => [row.student.sub, row.action])).toEqual([
      ['alina', 'move'],
      ['boris', 'add'],
    ])
  })

  it('без поиска отдаёт всех: кто на доске — перенести, остальные — добавить', () => {
    const rows = listAddSpecialistModalRows([onBoard, notOnBoard], new Set(['alina']), '')
    expect(rows.find((row) => row.student.sub === 'alina')?.action).toBe('move')
    expect(rows.find((row) => row.student.sub === 'boris')?.action).toBe('add')
  })

  it('не совпавший поиск — пустой список, не «все уже на доске»', () => {
    const rows = listAddSpecialistModalRows([onBoard], new Set(['alina']), 'zzzz')
    expect(rows).toEqual([])
  })
})
