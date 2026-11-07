import { describe, expect, it } from 'vitest'

import {
  KANBAN_DRAG_EDGE_MARGIN_PX,
  clientXFromActivatorEvent,
  dragPointerX,
  nextKanbanBoardScrollLeft,
  resolveKanbanDragEdgeDirection,
} from '../../../src/domain/kanban/kanbanDragScroll'

describe('resolveKanbanDragEdgeDirection', () => {
  const board = { left: 100, right: 500 }

  it('слева от зоны margin — left', () => {
    expect(resolveKanbanDragEdgeDirection(board, board.left + KANBAN_DRAG_EDGE_MARGIN_PX - 1)).toBe(
      'left',
    )
  })

  it('справа от зоны margin — right', () => {
    expect(resolveKanbanDragEdgeDirection(board, board.right - KANBAN_DRAG_EDGE_MARGIN_PX + 1)).toBe(
      'right',
    )
  })

  it('в середине — null', () => {
    expect(resolveKanbanDragEdgeDirection(board, 300)).toBeNull()
  })
})

describe('nextKanbanBoardScrollLeft', () => {
  it('влево не уходит ниже 0', () => {
    expect(nextKanbanBoardScrollLeft(5, 1000, 400, 'left', 14)).toBe(0)
  })

  it('вправо не превышает max', () => {
    expect(nextKanbanBoardScrollLeft(590, 1000, 400, 'right', 14)).toBe(600)
  })

  it('сдвигает на step внутри диапазона', () => {
    expect(nextKanbanBoardScrollLeft(100, 1000, 400, 'right', 14)).toBe(114)
    expect(nextKanbanBoardScrollLeft(100, 1000, 400, 'left', 14)).toBe(86)
  })
})

describe('dragPointerX', () => {
  it('предпочитает указатель (тачпад/мышь), а не центр широкой колонки', () => {
    expect(dragPointerX(120, 40, { left: 0, width: 400 })).toBe(160)
  })

  it('без clientX — центр translated-rect', () => {
    expect(dragPointerX(null, 10, { left: 100, width: 50 })).toBe(125)
  })

  it('без указателя и rect — null', () => {
    expect(dragPointerX(undefined, 0, null)).toBeNull()
  })
})

describe('clientXFromActivatorEvent', () => {
  it('берёт clientX у pointer/mouse', () => {
    const event = new Event('pointerdown') as Event & { clientX: number }
    event.clientX = 42
    expect(clientXFromActivatorEvent(event)).toBe(42)
  })

  it('берёт clientX у touch', () => {
    const event = new Event('touchstart') as Event & { touches: Array<{ clientX: number }> }
    event.touches = [{ clientX: 88 }]
    expect(clientXFromActivatorEvent(event)).toBe(88)
  })
})
