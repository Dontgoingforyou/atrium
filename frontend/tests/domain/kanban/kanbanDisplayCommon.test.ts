import { describe, expect, it } from 'vitest'
import {
  getKanbanDropOffset,
  mergeOrderedKeys,
  buildDisplayOrderWithOtherBucket,
  resolveKanbanInsertAnchorFromPointer,
  visibleKanbanInsertAnchor,
  kanbanInsertAnchorEquals,
  kanbanReorderPeerTasks,
  filterTasksByPriorityWithFamily,
  orderTasksForListView,
} from '../../../src/domain/kanban/kanbanDisplayCommon'

describe('getKanbanDropOffset', () => {
  const overRect = { top: 100, height: 80 } // midY = 140

  it('возвращает 0 (вставить перед) когда перетаскиваемый центр выше центра цели', () => {
    // activeMidY = 90 + 40 = 130 < 140 → вставить перед
    const active = { top: 90, height: 80 }
    expect(getKanbanDropOffset(overRect, active)).toBe(0)
  })

  it('возвращает 1 (вставить после) когда перетаскиваемый центр ниже центра цели', () => {
    // activeMidY = 160 + 40 = 200 > 140 → вставить после
    const active = { top: 160, height: 80 }
    expect(getKanbanDropOffset(overRect, active)).toBe(1)
  })

  it('возвращает 1 (вставить после) когда центры совпадают', () => {
    // activeMidY = 100 + 40 = 140 === 140 → вставить после (>=)
    const active = { top: 100, height: 80 }
    expect(getKanbanDropOffset(overRect, active)).toBe(1)
  })

  it('возвращает 0 когда activeTranslated равен null', () => {
    expect(getKanbanDropOffset(overRect, null)).toBe(0)
  })

  it('возвращает 0 когда activeTranslated равен undefined', () => {
    expect(getKanbanDropOffset(overRect, undefined)).toBe(0)
  })
})

describe('resolveKanbanInsertAnchorFromPointer', () => {
  const column = [{ id: 'a' }, { id: 'b' }, { id: 'c' }, { id: 'd' }]
  const rects = new Map([
    ['a', { top: 0, height: 80 }],
    ['b', { top: 90, height: 80 }],
    ['c', { top: 180, height: 80 }],
    ['d', { top: 270, height: 80 }],
  ])

  it('вниз на 2: b → после d (в конец)', () => {
    expect(resolveKanbanInsertAnchorFromPointer(column, 'b', 350, rects)).toEqual({
      afterTaskId: 'd',
      beforeTaskId: null,
    })
  })

  it('вниз на 1: b → между c и d (после c)', () => {
    expect(resolveKanbanInsertAnchorFromPointer(column, 'b', 250, rects)).toEqual({
      afterTaskId: 'c',
      beforeTaskId: null,
    })
  })

  it('вверх на 2: d → перед b (после a)', () => {
    expect(resolveKanbanInsertAnchorFromPointer(column, 'd', 100, rects)).toEqual({
      afterTaskId: 'a',
      beforeTaskId: null,
    })
  })

  it('вверх на 2: d → перед a (в начало)', () => {
    expect(resolveKanbanInsertAnchorFromPointer(column, 'd', 20, rects)).toEqual({
      afterTaskId: null,
      beforeTaskId: 'a',
    })
  })

  it('при null activeMidY сохраняет текущее место (перед тем же соседом)', () => {
    // 'b' сейчас на индексе 1 → остаётся перед 'c' (следующим соседом после неё)
    expect(resolveKanbanInsertAnchorFromPointer(column, 'b', null, rects)).toEqual({
      afterTaskId: null,
      beforeTaskId: 'c',
    })
  })

  it('единственная карточка в колонке — якорь пустой', () => {
    const single = [{ id: 'only' }]
    expect(resolveKanbanInsertAnchorFromPointer(single, 'only', 100, rects)).toEqual({
      afterTaskId: null,
      beforeTaskId: null,
    })
  })

  it('якорь по видимому порядку: между b и c', () => {
    expect(visibleKanbanInsertAnchor(column, 'b')).toEqual({
      afterTaskId: 'a',
      beforeTaskId: 'c',
    })
  })

  it('не считает разными одинаковые якоря', () => {
    const anchor = { afterTaskId: 'a', beforeTaskId: null as string | null }
    expect(kanbanInsertAnchorEquals(anchor, { afterTaskId: 'a', beforeTaskId: null })).toBe(true)
    expect(kanbanInsertAnchorEquals(anchor, { afterTaskId: null, beforeTaskId: 'c' })).toBe(false)
  })
})

describe('kanbanReorderPeerTasks', () => {
  const parent = { id: 'p', parent_task_id: null as string | null, status: 'todo' }
  const s1 = { id: 's1', parent_task_id: 'p', status: 'todo' }
  const s2 = { id: 's2', parent_task_id: 'p', status: 'todo' }
  const s3 = { id: 's3', parent_task_id: 'p', status: 'done' }
  const other = { id: 'o', parent_task_id: null as string | null, status: 'todo' }
  const columnVisible = [parent, other]
  const siblings = new Map([['p', [s1, s2, s3]]])
  const byId = new Map([
    ['p', parent],
    ['s1', s1],
    ['s2', s2],
    ['s3', s3],
    ['o', other],
  ])

  it('для nested-подзадачи возвращает siblings того же статуса', () => {
    expect(
      kanbanReorderPeerTasks(s2, 'todo', columnVisible, siblings, byId, false).map((t) => t.id),
    ).toEqual(['s1', 's2'])
  })

  it('в flat-режиме возвращает видимые карточки колонки', () => {
    expect(
      kanbanReorderPeerTasks(s2, 'todo', columnVisible, siblings, byId, true),
    ).toEqual(columnVisible)
  })

  it('для корневой задачи возвращает видимые карточки колонки', () => {
    expect(
      kanbanReorderPeerTasks(parent, 'todo', columnVisible, siblings, byId, false),
    ).toEqual(columnVisible)
  })
})

describe('mergeOrderedKeys', () => {
  it('сохраняет порядок из pref если все ключи присутствуют', () => {
    const result = mergeOrderedKeys(
      ['a', 'b', 'c'],
      ['c', 'a', 'b'],
      new Map([['a', 0], ['b', 1], ['c', 2]]),
    )
    expect(result).toEqual(['c', 'a', 'b'])
  })

  it('добавляет ключи отсутствующие в pref в конец', () => {
    const result = mergeOrderedKeys(
      ['a', 'b', 'c'],
      ['b'],
      new Map([['a', 0], ['b', 1], ['c', 2]]),
    )
    expect(result).toEqual(['b', 'a', 'c'])
  })

  it('при пустом pref сортирует по position', () => {
    const result = mergeOrderedKeys(
      ['c', 'a', 'b'],
      [],
      new Map([['a', 0], ['b', 1], ['c', 2]]),
    )
    expect(result).toEqual(['a', 'b', 'c'])
  })
})

describe('buildDisplayOrderWithOtherBucket', () => {
  it('добавляет KANBAN_OTHER_BUCKET в конец если есть скрытые задачи', () => {
    const result = buildDisplayOrderWithOtherBucket(
      ['todo', 'done'],
      new Set(['wip']),
      false,
      true,
    )
    expect(result[result.length - 1]).toBe('__portal_other__')
  })

  it('не добавляет KANBAN_OTHER_BUCKET если showAllHiddenColumns=true', () => {
    const result = buildDisplayOrderWithOtherBucket(
      ['todo', 'wip', 'done'],
      new Set(['wip']),
      true,
      true,
    )
    expect(result).toEqual(['todo', 'wip', 'done'])
    expect(result).not.toContain('__portal_other__')
  })
})

describe('filterTasksByPriorityWithFamily', () => {
  const tasks = [
    { id: 'parent', parent_task_id: null, priority: 'low' },
    { id: 'child', parent_task_id: 'parent', priority: 'high' },
    { id: 'other', parent_task_id: null, priority: 'medium' },
  ]

  it('возвращает все задачи без фильтра', () => {
    expect(filterTasksByPriorityWithFamily(tasks, [])).toEqual(tasks)
  })

  it('включает родителя при совпадении подзадачи', () => {
    const result = filterTasksByPriorityWithFamily(tasks, ['high'])
    expect(result.map((t) => t.id).sort()).toEqual(['child', 'parent'])
  })

  it('включает подзадачи при совпадении родителя', () => {
    const result = filterTasksByPriorityWithFamily(tasks, ['low'])
    expect(result.map((t) => t.id).sort()).toEqual(['child', 'parent'])
  })
})

describe('orderTasksForListView', () => {
  it('ставит подзадачи сразу после родителя', () => {
    const tasks = [
      { id: 'b', parent_task_id: null },
      { id: 'c1', parent_task_id: 'a' },
      { id: 'a', parent_task_id: null },
      { id: 'c2', parent_task_id: 'a' },
      { id: 'orphan', parent_task_id: 'missing' },
    ]
    expect(orderTasksForListView(tasks).map((t) => t.id)).toEqual([
      'b',
      'a',
      'c1',
      'c2',
      'orphan',
    ])
  })
})
