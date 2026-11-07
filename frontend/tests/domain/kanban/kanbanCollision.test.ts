import { describe, expect, it } from 'vitest'

import { resolveKanbanBoardCollisions } from '../../../src/domain/kanban/kanbanCollision'
import { KANBAN_OTHER_BUCKET } from '../../../src/domain/kanban/kanbanDisplayCommon'

const hit = (id: string) => ({ id })

const COLUMN_IDS = new Set(['todo', 'doing', 'done', KANBAN_OTHER_BUCKET])

function taskIdsInColumn(status: string): Set<string> {
  if (status === 'todo') return new Set(['task-a', 'task-b'])
  if (status === 'doing') return new Set(['task-c'])
  return new Set()
}

describe('resolveKanbanBoardCollisions — drag колонки', () => {
  it('указатель над карточкой — цель колонка, не задача', () => {
    const result = resolveKanbanBoardCollisions({
      activeType: 'column',
      activeId: 'todo',
      pointerHits: [hit('task-c'), hit('doing')],
      closestHits: [hit('task-c'), hit('doing'), hit('todo')],
      columnIds: COLUMN_IDS,
      taskIdsInColumn,
    })
    expect(result.map((h) => h.id)).toEqual(['doing'])
  })

  it('указатель над заголовком колонки с карточками — цель колонка', () => {
    const result = resolveKanbanBoardCollisions({
      activeType: 'column',
      activeId: 'todo',
      pointerHits: [hit('doing')],
      closestHits: [hit('task-c'), hit('doing')],
      columnIds: COLUMN_IDS,
      taskIdsInColumn,
    })
    expect(result.map((h) => h.id)).toEqual(['doing'])
  })

  it('зазор между колонками — ближайшая колонка по closestCenter', () => {
    const result = resolveKanbanBoardCollisions({
      activeType: 'column',
      activeId: 'todo',
      pointerHits: [],
      closestHits: [hit('task-c'), hit('doing'), hit('done')],
      columnIds: COLUMN_IDS,
      taskIdsInColumn,
    })
    expect(result.map((h) => h.id)).toEqual(['doing', 'done'])
  })

  it('колонку-агрегатор other не считает целью', () => {
    const result = resolveKanbanBoardCollisions({
      activeType: 'column',
      activeId: 'todo',
      pointerHits: [hit(KANBAN_OTHER_BUCKET)],
      closestHits: [hit(KANBAN_OTHER_BUCKET), hit('doing')],
      columnIds: COLUMN_IDS,
      taskIdsInColumn,
    })
    expect(result.map((h) => h.id)).toEqual(['doing'])
  })

  it('placeholder своей колонки не считает целью', () => {
    const result = resolveKanbanBoardCollisions({
      activeType: 'column',
      activeId: 'todo',
      pointerHits: [hit('todo'), hit('doing')],
      closestHits: [hit('todo'), hit('doing')],
      columnIds: COLUMN_IDS,
      taskIdsInColumn,
    })
    expect(result.map((h) => h.id)).toEqual(['doing'])
  })
})

describe('resolveKanbanBoardCollisions — drag задачи', () => {
  it('точное попадание в карточку важнее колонки', () => {
    const result = resolveKanbanBoardCollisions({
      activeType: 'task',
      activeId: 'task-a',
      pointerHits: [hit('task-c'), hit('doing')],
      closestHits: [hit('doing'), hit('task-c')],
      columnIds: COLUMN_IDS,
      taskIdsInColumn,
    })
    expect(result.map((h) => h.id)).toEqual(['task-c'])
  })

  it('указатель над колонкой / в зазоре карточек — ближайшая карточка той же колонки', () => {
    const result = resolveKanbanBoardCollisions({
      activeType: 'task',
      activeId: 'task-a',
      pointerHits: [hit('todo')],
      closestHits: [hit('task-b'), hit('todo'), hit('task-c')],
      columnIds: COLUMN_IDS,
      taskIdsInColumn,
    })
    expect(result.map((h) => h.id)).toEqual(['task-b'])
  })

  it('пустая колонка — сама колонка', () => {
    const result = resolveKanbanBoardCollisions({
      activeType: 'task',
      activeId: 'task-a',
      pointerHits: [hit('done')],
      closestHits: [hit('done'), hit('task-c')],
      columnIds: COLUMN_IDS,
      taskIdsInColumn,
    })
    expect(result.map((h) => h.id)).toEqual(['done'])
  })
})

describe('resolveKanbanBoardCollisions — drag карточки специалиста', () => {
  const specialistColumns = new Set(['na-proekte', 'peredat-vo-vne', 'uvolen'])

  function specialistIdsInColumn(columnKey: string): Set<string> {
    if (columnKey === 'na-proekte') return new Set(['spec-a'])
    if (columnKey === 'uvolen') return new Set(['spec-b', 'spec-c'])
    return new Set()
  }

  it('указатель над пустой «Передать во вне» — колонка, не соседняя карточка', () => {
    const result = resolveKanbanBoardCollisions({
      activeType: 'specialist-entry',
      activeId: 'spec-b',
      pointerHits: [hit('peredat-vo-vne')],
      closestHits: [hit('spec-a'), hit('na-proekte'), hit('peredat-vo-vne')],
      columnIds: specialistColumns,
      taskIdsInColumn: specialistIdsInColumn,
    })
    expect(result.map((h) => h.id)).toEqual(['peredat-vo-vne'])
  })
})
