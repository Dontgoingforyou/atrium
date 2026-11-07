import { describe, expect, it } from 'vitest'

import {
  clampHorizontalLeft,
  computeAnchoredMenuPlacement,
  computeVerticalDropdownPlacement,
  DROPDOWN_GAP,
  DROPDOWN_MIN_VISIBLE_HEIGHT,
  DROPDOWN_SCREEN_MARGIN,
} from '../../src/hooks/dropdownPlacement'

function rect(top: number, bottom: number, left = 0, right = 100): DOMRect {
  return {
    top,
    bottom,
    left,
    right,
    width: right - left,
    height: bottom - top,
    x: left,
    y: top,
    toJSON: () => ({}),
  } as DOMRect
}

describe('computeVerticalDropdownPlacement', () => {
  it('открывается вниз, когда снизу достаточно места', () => {
    const anchor = rect(100, 130)
    const result = computeVerticalDropdownPlacement(anchor, 800, 280)

    expect(result.openUp).toBe(false)
    expect(result.top).toBe(130 + DROPDOWN_GAP)
    expect(result.maxHeight).toBe(280)
  })

  it('открывается вверх, когда снизу мало места, а сверху больше', () => {
    const anchor = rect(700, 730)
    const result = computeVerticalDropdownPlacement(anchor, 800, 280)

    expect(result.openUp).toBe(true)
    expect(result.top).toBe(700 - result.maxHeight - DROPDOWN_GAP)
    expect(result.maxHeight).toBeLessThanOrEqual(280)
    expect(result.maxHeight).toBeGreaterThanOrEqual(DROPDOWN_MIN_VISIBLE_HEIGHT)
  })
})

describe('computeAnchoredMenuPlacement', () => {
  it('открывается вниз, если меню помещается', () => {
    const anchor = rect(100, 130)
    const result = computeAnchoredMenuPlacement(anchor, 800, 180)

    expect(result.openUp).toBe(false)
    expect(result.top).toBe(130 + DROPDOWN_GAP)
    expect(result.maxHeight).toBe(180)
  })

  it('открывается вверх у нижнего края viewport', () => {
    const anchor = rect(720, 750)
    const menuHeight = 200
    const result = computeAnchoredMenuPlacement(anchor, 800, menuHeight)

    expect(result.openUp).toBe(true)
    expect(result.top).toBe(720 - menuHeight - DROPDOWN_GAP)
    expect(result.maxHeight).toBe(menuHeight)
  })

  it('ограничивает maxHeight и открывает вверх, если меню не помещается целиком', () => {
    const anchor = rect(720, 750)
    const result = computeAnchoredMenuPlacement(anchor, 800, 800)

    expect(result.openUp).toBe(true)
    expect(result.maxHeight).toBe(720 - DROPDOWN_SCREEN_MARGIN)
    expect(result.top).toBe(720 - result.maxHeight - DROPDOWN_GAP)
  })
})

describe('clampHorizontalLeft', () => {
  it('выравнивает меню по правому краю якоря с учётом viewport', () => {
    const anchor = rect(0, 30, 200, 260)
    expect(clampHorizontalLeft(anchor, 220, 400)).toBe(40)
  })

  it('не уходит за левый край экрана', () => {
    const anchor = rect(0, 30, 10, 50)
    expect(clampHorizontalLeft(anchor, 220, 400)).toBe(DROPDOWN_SCREEN_MARGIN)
  })

  it('не уходит за правый край экрана', () => {
    const anchor = rect(0, 30, 360, 399)
    expect(clampHorizontalLeft(anchor, 50, 400)).toBe(400 - 50 - DROPDOWN_SCREEN_MARGIN)
  })
})
