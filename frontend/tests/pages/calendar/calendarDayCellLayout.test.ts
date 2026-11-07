import { describe, expect, it } from 'vitest'

import {
  CHIP_GAP_PX,
  CHIP_HEIGHT_PX,
  MAX_COLLAPSED_CHIPS,
  MORE_BTN_HEIGHT_PX,
  maxVisibleChips,
} from '../../../src/pages/calendar/calendarDayCellLayout'

describe('maxVisibleChips', () => {
  it('пустой список — 0', () => {
    expect(maxVisibleChips(100, 0)).toBe(0)
  })

  it('без высоты — не больше MAX_COLLAPSED_CHIPS', () => {
    expect(maxVisibleChips(0, 10)).toBe(MAX_COLLAPSED_CHIPS)
    expect(maxVisibleChips(0, 2)).toBe(2)
  })

  it('если всё влезает — показывает все (с потолком)', () => {
    const h = 5 * (CHIP_HEIGHT_PX + CHIP_GAP_PX)
    expect(maxVisibleChips(h, 3)).toBe(3)
    expect(maxVisibleChips(h, 5)).toBe(5)
  })

  it('на низкой ячейке резервирует место под «+N»', () => {
    // ~3 чипа без кнопки, с кнопкой — максимум 2
    const h = 3 * CHIP_HEIGHT_PX + 2 * CHIP_GAP_PX
    expect(maxVisibleChips(h, 4)).toBeLessThan(4)
    expect(maxVisibleChips(h, 4)).toBeGreaterThanOrEqual(1)
    const expected = Math.floor((h - MORE_BTN_HEIGHT_PX + CHIP_GAP_PX) / (CHIP_HEIGHT_PX + CHIP_GAP_PX))
    expect(maxVisibleChips(h, 4)).toBe(Math.max(0, Math.min(expected, MAX_COLLAPSED_CHIPS, 3)))
  })

  it('не превышает MAX_COLLAPSED_CHIPS', () => {
    expect(maxVisibleChips(10_000, 20)).toBe(MAX_COLLAPSED_CHIPS)
  })
})
