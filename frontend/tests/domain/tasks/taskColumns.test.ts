import { describe, expect, it } from 'vitest'
import type { PortalTaskColumn } from '../../../src/types/task'
import {
  buildTaskStatusSelectOptions,
  getTaskColumnTitle,
  isApprovalLikeColumnTitle,
  isClosedColumnStatus,
  isDoneLikeColumnTitle,
  isKpiExcludedStatus,
  isSubtaskProgressDone,
  isTaskOverdue,
  shouldPlayTaskDoneSuccess,
} from '../../../src/domain/tasks/taskColumns'

const columns: PortalTaskColumn[] = [
  {
    id: '1',
    title: 'Бэклог',
    color: '#6131cf',
    status_key: 'todo',
    position: 0,
    exclude_from_kpi: false,
  },
  {
    id: '2',
    title: 'Готово',
    color: '#7a7a7a',
    status_key: 'col_done',
    position: 1,
    exclude_from_kpi: false,
  },
  {
    id: '3',
    title: 'На согласовании',
    color: '#3b82f6',
    status_key: 'on_approval',
    position: 2,
    exclude_from_kpi: true,
  },
]

describe('taskColumns', () => {
  it('getTaskColumnTitle uses column title', () => {
    expect(getTaskColumnTitle('todo', columns)).toBe('Бэклог')
  })

  it('isKpiExcludedStatus respects exclude_from_kpi flag', () => {
    expect(isKpiExcludedStatus('on_approval', columns)).toBe(true)
    expect(isKpiExcludedStatus('todo', columns)).toBe(false)
  })

  it('buildTaskStatusSelectOptions adds orphan current status', () => {
    const opts = buildTaskStatusSelectOptions(columns, 'orphan_status')
    expect(opts.map((o) => o.value)).toEqual(['todo', 'col_done', 'on_approval', 'orphan_status'])
  })

  it('isTaskOverdue returns false for done task with past due_at', () => {
    const past = '2000-01-01T00:00:00Z'
    expect(isTaskOverdue({ status: 'done', due_at: past }, columns)).toBe(false)
    expect(isTaskOverdue({ status: 'col_done', due_at: past }, columns)).toBe(false)
    expect(isTaskOverdue({ status: 'on_approval', due_at: past }, columns)).toBe(false)
  })

  it('isTaskOverdue: вчера просрочено, сегодня и завтра — нет', () => {
    const d = new Date()
    const y = d.getFullYear()
    const m = String(d.getMonth() + 1).padStart(2, '0')
    const day = d.getDate()
    const today = `${y}-${m}-${String(day).padStart(2, '0')}`
    const yesterdayDate = new Date(y, d.getMonth(), day - 1)
    const tomorrowDate = new Date(y, d.getMonth(), day + 1)
    const yesterday = `${yesterdayDate.getFullYear()}-${String(yesterdayDate.getMonth() + 1).padStart(2, '0')}-${String(yesterdayDate.getDate()).padStart(2, '0')}`
    const tomorrow = `${tomorrowDate.getFullYear()}-${String(tomorrowDate.getMonth() + 1).padStart(2, '0')}-${String(tomorrowDate.getDate()).padStart(2, '0')}`
    expect(isTaskOverdue({ status: 'todo', due_at: `${yesterday}T00:00:00Z` }, columns)).toBe(true)
    expect(isTaskOverdue({ status: 'todo', due_at: today }, columns)).toBe(false)
    expect(isTaskOverdue({ status: 'todo', due_at: `${tomorrow}T12:00:00Z` }, columns)).toBe(false)
  })

  it('isSubtaskProgressDone: done/cancelled и «Готово» по title, не exclude_from_kpi', () => {
    expect(isSubtaskProgressDone('done', columns)).toBe(true)
    expect(isSubtaskProgressDone('cancelled', columns)).toBe(true)
    expect(isSubtaskProgressDone('col_done', columns)).toBe(true)
    expect(isSubtaskProgressDone('on_approval', columns)).toBe(false)
    expect(isSubtaskProgressDone('todo', columns)).toBe(false)
    expect(isSubtaskProgressDone('in_progress', columns)).toBe(false)
  })

  it('shouldPlayTaskDoneSuccess: только вход в done-like', () => {
    expect(shouldPlayTaskDoneSuccess('todo', 'done', columns)).toBe(true)
    expect(shouldPlayTaskDoneSuccess('todo', 'col_done', columns)).toBe(true)
    expect(shouldPlayTaskDoneSuccess('done', 'done', columns)).toBe(false)
    expect(shouldPlayTaskDoneSuccess('col_done', 'col_done', columns)).toBe(false)
    expect(shouldPlayTaskDoneSuccess('done', 'todo', columns)).toBe(false)
    expect(shouldPlayTaskDoneSuccess('todo', 'in_progress', columns)).toBe(false)
  })

  it('title-предикаты: Готово / На согласовании / отмена', () => {
    expect(isDoneLikeColumnTitle('Готово')).toBe(true)
    expect(isDoneLikeColumnTitle('готовые')).toBe(true)
    expect(isDoneLikeColumnTitle('На согласовании')).toBe(false)
    expect(isApprovalLikeColumnTitle('На согласовании')).toBe(true)
    expect(isApprovalLikeColumnTitle('Готово')).toBe(false)
  })

  it('status_key=done с title «На согласовании» — закрыто, но не прогресс «Готово»', () => {
    const prodColumns: PortalTaskColumn[] = [
      {
        id: 'p1',
        title: 'На согласовании',
        color: '#3b82f6',
        status_key: 'done',
        position: 0,
        exclude_from_kpi: true,
      },
      {
        id: 'p2',
        title: 'Готово',
        color: '#1a9000',
        status_key: 'col_o4kqsv03',
        position: 1,
        exclude_from_kpi: false,
      },
    ]
    expect(isClosedColumnStatus('done', prodColumns)).toBe(true)
    expect(isClosedColumnStatus('col_o4kqsv03', prodColumns)).toBe(true)
    expect(isSubtaskProgressDone('done', prodColumns)).toBe(false)
    expect(isSubtaskProgressDone('col_o4kqsv03', prodColumns)).toBe(true)
    expect(shouldPlayTaskDoneSuccess('todo', 'done', prodColumns)).toBe(false)
    expect(shouldPlayTaskDoneSuccess('todo', 'col_o4kqsv03', prodColumns)).toBe(true)
    const past = '2000-01-01T00:00:00Z'
    expect(isTaskOverdue({ status: 'col_o4kqsv03', due_at: past }, prodColumns)).toBe(false)
    expect(isTaskOverdue({ status: 'done', due_at: past }, prodColumns)).toBe(false)
  })
})
