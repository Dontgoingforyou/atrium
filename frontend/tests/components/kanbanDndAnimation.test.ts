import { describe, expect, it } from 'vitest'

import {
  isKanbanColumnDropHidden,
  kanbanColumnOverlayWidth,
  KANBAN_COLUMN_DROP_ANIMATION,
  KANBAN_COLUMN_OVERLAY_FALLBACK_WIDTH_PX,
} from '../../src/components/tasks/kanban/kanbanDndAnimation'

describe('isKanbanColumnDropHidden', () => {
  it('скрывает колонку, пока overlay долетает', () => {
    expect(isKanbanColumnDropHidden('todo', 'todo', null)).toBe(true)
  })

  it('показывает колонку в фазе разворота', () => {
    expect(isKanbanColumnDropHidden('todo', 'todo', 'todo')).toBe(false)
  })

  it('не скрывает соседние колонки', () => {
    expect(isKanbanColumnDropHidden('doing', 'todo', null)).toBe(false)
  })

  it('не скрывает, когда анимация не идёт', () => {
    expect(isKanbanColumnDropHidden('todo', null, null)).toBe(false)
  })
})

describe('kanbanColumnOverlayWidth', () => {
  it('берёт ширину из rect', () => {
    expect(kanbanColumnOverlayWidth({ width: 340 })).toBe(340)
  })

  it('без rect — запасная ширина колонки', () => {
    expect(kanbanColumnOverlayWidth(null)).toBe(KANBAN_COLUMN_OVERLAY_FALLBACK_WIDTH_PX)
  })
})

describe('KANBAN_COLUMN_DROP_ANIMATION', () => {
  it('не использует defaultDropAnimationSideEffects — пустой setup/cleanup', () => {
    // DropAnimation = объект | функция; сужаем до конфига с sideEffects.
    expect(typeof KANBAN_COLUMN_DROP_ANIMATION).toBe('object')
    if (typeof KANBAN_COLUMN_DROP_ANIMATION === 'function') {
      throw new Error('ожидался объект DropAnimation, не функция')
    }
    const sideEffects = KANBAN_COLUMN_DROP_ANIMATION.sideEffects
    expect(sideEffects).toBeTypeOf('function')
    const cleanup = sideEffects?.({} as never)
    expect(cleanup).toBeTypeOf('function')
    expect(cleanup).not.toBe(sideEffects)
  })
})
