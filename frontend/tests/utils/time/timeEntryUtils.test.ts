import { describe, expect, it } from 'vitest'
import {
  buildDuplicateTimeEntryCreate,
  formatMinutes,
  generateWeekdayDates,
  groupEntriesByDay,
  monthToDateRange,
  parseHoursToMinutes,
  MAX_ENTRY_MINUTES_PER_DAY,
  TARGET_DAY_MINUTES,
} from '@/utils/time/timeEntryUtils'
import type { PortalTimeEntry } from '@/types/timeEntry'

function makeEntry(overrides: Partial<PortalTimeEntry>): PortalTimeEntry {
  return {
    id: 'id-1',
    user_sub: 'user-sub',
    task_id: null,
    task_name: null,
    worked_on: '2026-05-05',
    minutes: 60,
    note: null,
    version: 1,
    created_at: '2026-05-05T10:00:00Z',
    updated_at: '2026-05-05T10:00:00Z',
    ...overrides,
  }
}

describe('TARGET_DAY_MINUTES', () => {
  it('равно 8 часам (480 минут)', () => {
    expect(TARGET_DAY_MINUTES).toBe(480)
  })
})

describe('parseHoursToMinutes', () => {
  it('переводит дробные часы в минуты', () => {
    expect(parseHoursToMinutes('1.5')).toBe(90)
    expect(parseHoursToMinutes('8')).toBe(480)
  })

  it('возвращает null для 0, отрицательных и сверх суток', () => {
    expect(parseHoursToMinutes('0')).toBeNull()
    expect(parseHoursToMinutes('-1')).toBeNull()
    expect(parseHoursToMinutes(String(MAX_ENTRY_MINUTES_PER_DAY / 60 + 1))).toBeNull()
  })
})

describe('groupEntriesByDay', () => {
  it('возвращает пустой массив для пустого списка записей', () => {
    expect(groupEntriesByDay([])).toEqual([])
  })

  it('группирует несколько записей одного дня в одну группу с суммой минут', () => {
    const entries = [
      makeEntry({ id: '1', worked_on: '2026-05-05', minutes: 120 }),
      makeEntry({ id: '2', worked_on: '2026-05-05', minutes: 90 }),
    ]
    const groups = groupEntriesByDay(entries)
    expect(groups).toHaveLength(1)
    expect(groups[0].worked_on).toBe('2026-05-05')
    expect(groups[0].totalMinutes).toBe(210)
    expect(groups[0].entries).toHaveLength(2)
  })

  it('сохраняет порядок появления дней из входного списка (список уже отсортирован бэкендом)', () => {
    const entries = [
      makeEntry({ id: '1', worked_on: '2026-05-06', minutes: 60 }),
      makeEntry({ id: '2', worked_on: '2026-05-05', minutes: 60 }),
      makeEntry({ id: '3', worked_on: '2026-05-06', minutes: 30 }),
    ]
    const groups = groupEntriesByDay(entries)
    expect(groups.map((g) => g.worked_on)).toEqual(['2026-05-06', '2026-05-05'])
    expect(groups[0].totalMinutes).toBe(90)
    expect(groups[1].totalMinutes).toBe(60)
  })

  it('не мутирует порядок записей внутри дня', () => {
    const e1 = makeEntry({ id: '1', worked_on: '2026-05-05', minutes: 60 })
    const e2 = makeEntry({ id: '2', worked_on: '2026-05-05', minutes: 30 })
    const groups = groupEntriesByDay([e1, e2])
    expect(groups[0].entries).toEqual([e1, e2])
  })
})

describe('generateWeekdayDates', () => {
  it('по умолчанию (Пн-Пт) возвращает будние дни недельного диапазона', () => {
    // 2026-06-01 (пн) — 2026-06-07 (вс)
    const dates = generateWeekdayDates('2026-06-01', '2026-06-07', [0, 1, 2, 3, 4])
    expect(dates).toEqual(['2026-06-01', '2026-06-02', '2026-06-03', '2026-06-04', '2026-06-05'])
  })

  it('фильтрует по нестандартному набору дней недели (только сб/вс)', () => {
    const dates = generateWeekdayDates('2026-06-01', '2026-06-07', [5, 6])
    expect(dates).toEqual(['2026-06-06', '2026-06-07'])
  })

  it('возвращает один день, если date_from === date_to и день подходит', () => {
    const dates = generateWeekdayDates('2026-06-01', '2026-06-01', [0, 1, 2, 3, 4])
    expect(dates).toEqual(['2026-06-01'])
  })

  it('возвращает пустой список, если диапазон не содержит подходящих дней недели', () => {
    const dates = generateWeekdayDates('2026-06-01', '2026-06-01', [5, 6])
    expect(dates).toEqual([])
  })

  it('возвращает пустой список, если date_to раньше date_from', () => {
    const dates = generateWeekdayDates('2026-06-10', '2026-06-01', [0, 1, 2, 3, 4])
    expect(dates).toEqual([])
  })

  it('возвращает пустой список при незаполненных датах', () => {
    expect(generateWeekdayDates('', '2026-06-07', [0])).toEqual([])
    expect(generateWeekdayDates('2026-06-01', '', [0])).toEqual([])
  })
})

describe('buildDuplicateTimeEntryCreate', () => {
  it('копирует task_id/названия и подставляет новые дату и минуты', () => {
    const entry = makeEntry({
      task_id: 'task-uuid',
      task_name: 'Фича',
      note: 'ревью',
      worked_on: '2026-05-01',
      minutes: 90,
    })
    expect(
      buildDuplicateTimeEntryCreate(entry, {
        worked_on: '2026-05-10',
        minutes: 120,
        task_name: 'Фича ',
        note: 'ревью ',
      }),
    ).toEqual({
      worked_on: '2026-05-10',
      minutes: 120,
      task_id: 'task-uuid',
      task_name: 'Фича',
      note: 'ревью',
    })
  })
})

describe('formatMinutes', () => {
  it('0 минут → «0 мин»', () => {
    expect(formatMinutes(0)).toBe('0 мин')
  })

  it('ровно часы → «N ч» без минут', () => {
    expect(formatMinutes(60)).toBe('1 ч')
    expect(formatMinutes(120)).toBe('2 ч')
  })

  it('смешанное значение → «N ч M мин»', () => {
    expect(formatMinutes(90)).toBe('1 ч 30 мин')
    expect(formatMinutes(125)).toBe('2 ч 5 мин')
  })
})

describe('monthToDateRange', () => {
  it('возвращает первый и последний день месяца', () => {
    expect(monthToDateRange('2026-05')).toEqual({ from: '2026-05-01', to: '2026-05-31' })
  })

  it('корректно обрабатывает февраль невисокосного года (28 дней)', () => {
    expect(monthToDateRange('2026-02')).toEqual({ from: '2026-02-01', to: '2026-02-28' })
  })

  it('корректно обрабатывает февраль високосного года (29 дней)', () => {
    expect(monthToDateRange('2024-02')).toEqual({ from: '2024-02-01', to: '2024-02-29' })
  })

  it('декабрь — 31 день, переход на январь не сломан', () => {
    expect(monthToDateRange('2026-12')).toEqual({ from: '2026-12-01', to: '2026-12-31' })
  })

  it('апрель (30 дней) — не 31', () => {
    expect(monthToDateRange('2026-04')).toEqual({ from: '2026-04-01', to: '2026-04-30' })
  })
})
