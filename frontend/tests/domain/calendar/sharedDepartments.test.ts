import { describe, expect, it } from 'vitest'

import {
  departmentLabel,
  departmentsMatchingQuery,
  groupCalendarsByDepartment,
  type SharedDepartmentCalendar,
} from '@/domain/calendar/sharedDepartments'

function calendar(patch: Partial<SharedDepartmentCalendar> & Pick<SharedDepartmentCalendar, 'id'>): SharedDepartmentCalendar {
  return {
    owner_sub: 'sub',
    owner_label: 'Имя',
    title: 'Мой календарь',
    department_id: '10000',
    department_label: 'Аутстафф',
    show_to_other_departments: true,
    ...patch,
  }
}

describe('groupCalendarsByDepartment', () => {
  it('собирает людей с галочкой в отдел', () => {
    const groups = groupCalendarsByDepartment([
      calendar({ id: 'a', owner_sub: 'one', owner_label: 'Анна' }),
      calendar({
        id: 'b',
        owner_sub: 'two',
        owner_label: 'Борис',
        department_id: '10006',
        department_label: '10006',
      }),
    ])

    expect(groups.map((group) => group.label)).toEqual(['', 'Аутстафф'])
    expect(groups[1]?.calendars.map((item) => item.owner_sub)).toEqual(['one'])
  })

  it('не кладёт календарь без галочки и пустой отдел не появляется', () => {
    const groups = groupCalendarsByDepartment([
      calendar({ id: 'off', show_to_other_departments: false }),
    ])

    expect(groups).toEqual([])
  })
})

describe('departmentLabel', () => {
  it('подписывает свой отдел', () => {
    expect(departmentLabel('10000')).toBe('Аутстафф')
    expect(departmentLabel('10006')).toBe('')
    expect(departmentLabel(null)).toBe('Без отдела')
  })
})

describe('departmentsMatchingQuery', () => {
  const groups = groupCalendarsByDepartment([
    calendar({ id: 'a' }),
    calendar({ id: 'b', department_id: '10006', department_label: '10006' }),
  ])

  it('ищет по названию отдела', () => {
    expect(departmentsMatchingQuery(groups, 'аут').map((group) => group.departmentId)).toEqual(['10000'])
    expect(departmentsMatchingQuery(groups, '10006')).toEqual([])
  })
})
