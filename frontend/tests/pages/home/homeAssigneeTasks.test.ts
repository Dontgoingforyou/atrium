import { describe, expect, it } from 'vitest'
import type { PortalTask, PortalTaskColumn } from '../../../src/types/task'
import {
  extraAssigneeLoadRows,
  filterHomeAssigneeTasks,
  hiddenCount,
  homeOnTrackCount,
  isKpiActiveOpenTask,
  kpiActiveOpenStatusKeys,
  overduePreviewTasks,
  visibleAssigneeLoadRows,
} from '../../../src/pages/home/homeAssigneeTasks'
import { HOME_ASSIGNEE_TILE_LIMIT, homeQueryKeys } from '../../../src/pages/home/homeQueryKeys'
import { PORTAL_HOME_QUERY_KEY } from '../../../src/api/queryKeys'

const columns: PortalTaskColumn[] = [
  {
    id: '1',
    title: 'Бэклог',
    color: '#6131cf',
    status_key: 'todo',
    position: 1,
    exclude_from_kpi: false,
  },
  {
    id: '2',
    title: 'Готово',
    color: '#7a7a7a',
    status_key: 'col_done',
    position: 2,
    exclude_from_kpi: false,
  },
  {
    id: '3',
    title: 'На согласовании',
    color: '#3b82f6',
    status_key: 'on_approval',
    position: 0,
    exclude_from_kpi: true,
  },
]

function task(over: Partial<PortalTask> & Pick<PortalTask, 'id' | 'status'>): PortalTask {
  return {
    number: 1,
    title: over.id,
    description: null,
    creator_sub: 'c',
    assignee_sub: 'a',
    assignee_subs: ['a'],
    priority: 'medium',
    due_at: null,
    document_id: null,
    chat_id: null,
    source_message_id: null,
    parent_task_id: null,
    position: 0,
    version: 1,
    created_at: '',
    updated_at: '',
    tags: [],
    ...over,
  }
}

describe('homeOnTrackCount / hiddenCount', () => {
  it('считает «в срок» как open минус overdue, не ниже нуля', () => {
    expect(homeOnTrackCount(10, 3)).toBe(7)
    expect(homeOnTrackCount(2, 5)).toBe(0)
  })

  it('hiddenCount не уходит в минус', () => {
    expect(hiddenCount(20, HOME_ASSIGNEE_TILE_LIMIT)).toBe(16)
    expect(hiddenCount(3, HOME_ASSIGNEE_TILE_LIMIT)).toBe(0)
  })
})

describe('visibleAssigneeLoadRows', () => {
  const rows = Array.from({ length: 11 }, (_, i) => i)

  it('свёрнуто: первые limit, hiddenCount = остальные', () => {
    expect(visibleAssigneeLoadRows(rows, HOME_ASSIGNEE_TILE_LIMIT, false)).toEqual(rows.slice(0, 4))
    expect(hiddenCount(rows.length, HOME_ASSIGNEE_TILE_LIMIT)).toBe(7)
  })

  it('раскрыто: все строки', () => {
    expect(visibleAssigneeLoadRows(rows, HOME_ASSIGNEE_TILE_LIMIT, true)).toEqual(rows)
  })

  it('length <= limit — скрытых нет, свёртка не режет', () => {
    const short = [1, 2, 3]
    expect(hiddenCount(short.length, HOME_ASSIGNEE_TILE_LIMIT)).toBe(0)
    expect(visibleAssigneeLoadRows(short, HOME_ASSIGNEE_TILE_LIMIT, false)).toEqual(short)
    expect(visibleAssigneeLoadRows(short, HOME_ASSIGNEE_TILE_LIMIT, true)).toEqual(short)
    expect(extraAssigneeLoadRows(short, HOME_ASSIGNEE_TILE_LIMIT)).toEqual([])
  })

  it('extra — хвост после limit, чтобы слот анимации всегда держал плитки в DOM', () => {
    expect(extraAssigneeLoadRows(rows, HOME_ASSIGNEE_TILE_LIMIT)).toEqual(rows.slice(4))
  })
})

describe('homeQueryKeys', () => {
  it('assignee-ключи начинаются с PORTAL_HOME_QUERY_KEY', () => {
    expect(homeQueryKeys.assignee('sub-1').slice(0, 2)).toEqual([...PORTAL_HOME_QUERY_KEY])
    expect(homeQueryKeys.assigneeTasks('sub-1', ['todo'], 'open')[2]).toBe('assignee-tasks')
  })
})

describe('filterHomeAssigneeTasks', () => {
  const yesterday = (() => {
    const d = new Date()
    d.setDate(d.getDate() - 1)
    const y = d.getFullYear()
    const m = String(d.getMonth() + 1).padStart(2, '0')
    const day = String(d.getDate()).padStart(2, '0')
    return `${y}-${m}-${day}T00:00:00Z`
  })()

  const open = task({ id: 'open', status: 'todo' })
  const overdue = task({ id: 'overdue', status: 'todo', due_at: yesterday })
  const kpiExcluded = task({ id: 'kpi', status: 'on_approval' })
  const doneLike = task({ id: 'done', status: 'col_done' })

  it('open: только KPI-активные непросроченные', () => {
    const ids = filterHomeAssigneeTasks(
      [open, overdue, kpiExcluded, doneLike],
      columns,
      'open',
    ).map((t) => t.id)
    expect(ids).toEqual(['open'])
  })

  it('overdue: только просроченные KPI-активные', () => {
    const ids = filterHomeAssigneeTasks(
      [open, overdue, kpiExcluded],
      columns,
      'overdue',
    ).map((t) => t.id)
    expect(ids).toEqual(['overdue'])
  })

  it('all: не фильтрует (статусы уже с API)', () => {
    const rows = [open, kpiExcluded]
    expect(filterHomeAssigneeTasks(rows, columns, 'all')).toEqual(rows)
  })

  it('isKpiActiveOpenTask отсекает exclude_from_kpi и done-like', () => {
    expect(isKpiActiveOpenTask(open, columns)).toBe(true)
    expect(isKpiActiveOpenTask(kpiExcluded, columns)).toBe(false)
    expect(isKpiActiveOpenTask(doneLike, columns)).toBe(false)
  })

  it('kpiActiveOpenStatusKeys оставляет только KPI-открытые колонки по position', () => {
    const withInProgress: PortalTaskColumn[] = [
      ...columns,
      {
        id: '4',
        title: 'В работе',
        color: '#22c55e',
        status_key: 'in_progress',
        position: 0.5,
        exclude_from_kpi: false,
      },
      {
        id: '5',
        title: 'Архив',
        color: '#999',
        status_key: 'done',
        position: 9,
        exclude_from_kpi: false,
      },
    ]
    expect(kpiActiveOpenStatusKeys(withInProgress)).toEqual(['in_progress', 'todo', 'done'])
  })

  it('kpiActiveOpenStatusKeys: пустой список и только архив', () => {
    expect(kpiActiveOpenStatusKeys([])).toEqual([])
    expect(
      kpiActiveOpenStatusKeys([
        {
          id: 'd',
          title: 'Готово',
          color: '#7a7a7a',
          status_key: 'col_done',
          position: 0,
          exclude_from_kpi: false,
        },
      ]),
    ).toEqual([])
  })

  it('prod-like: «Готово» без флага и «На согласовании» с ключом done не в open', () => {
    const prodColumns: PortalTaskColumn[] = [
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
        title: 'На согласовании',
        color: '#3b82f6',
        status_key: 'done',
        position: 1,
        exclude_from_kpi: true,
      },
      {
        id: '3',
        title: 'Готово',
        color: '#1a9000',
        status_key: 'col_o4kqsv03',
        position: 2,
        exclude_from_kpi: false,
      },
    ]
    expect(isKpiActiveOpenTask(task({ id: 'ready', status: 'col_o4kqsv03' }), prodColumns)).toBe(false)
    expect(isKpiActiveOpenTask(task({ id: 'appr', status: 'done' }), prodColumns)).toBe(false)
    expect(isKpiActiveOpenTask(task({ id: 'open', status: 'todo' }), prodColumns)).toBe(true)
    expect(kpiActiveOpenStatusKeys(prodColumns)).toEqual(['todo'])
  })

  it('overduePreviewTasks не оставляет пустую секцию из непросроченных', () => {
    expect(overduePreviewTasks([open, kpiExcluded], columns)).toEqual([])
    expect(overduePreviewTasks([overdue], columns).map((t) => t.id)).toEqual(['overdue'])
  })
})
