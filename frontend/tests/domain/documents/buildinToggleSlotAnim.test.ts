// @vitest-environment jsdom

import { describe, expect, it } from 'vitest'

import {
  applyToggleSlotHeightSettled,
  measureToggleSlotNaturalHeight,
  resolveToggleSlotAnimHeights,
  settleBuildinToggleSlotHeight,
  shouldSkipToggleSlotAnim,
} from '@/domain/documents/buildinToggleSlotAnim'

describe('resolveToggleSlotAnimHeights', () => {
  it('раскрытие: от текущей высоты к натуральной', () => {
    expect(resolveToggleSlotAnimHeights(0, 120, true)).toEqual({ from: 0, to: 120 })
  })

  it('сворачивание: от текущей высоты к нулю, не к натуральной', () => {
    expect(resolveToggleSlotAnimHeights(120, 120, false)).toEqual({ from: 120, to: 0 })
  })
})

describe('shouldSkipToggleSlotAnim', () => {
  it('пропускает нулевую длительность и совпадающие края', () => {
    expect(shouldSkipToggleSlotAnim(0, 80, 0)).toBe(true)
    expect(shouldSkipToggleSlotAnim(80, 80, 250)).toBe(true)
    expect(shouldSkipToggleSlotAnim(0, 80, 250)).toBe(false)
  })
})

describe('applyToggleSlotHeightSettled', () => {
  it('открытый слот без inline height, закрытый — 0px', () => {
    const slot = document.createElement('div')
    slot.style.height = '80px'
    slot.style.overflow = 'hidden'
    applyToggleSlotHeightSettled(slot, true)
    expect(slot.style.height).toBe('')
    expect(slot.style.overflow).toBe('')
    applyToggleSlotHeightSettled(slot, false)
    expect(slot.style.height).toBe('0px')
    expect(slot.style.overflow).toBe('hidden')
  })
})

describe('settleBuildinToggleSlotHeight', () => {
  it('сразу ставит высоту без анимации', () => {
    const slot = document.createElement('div')
    slot.style.height = '80px'
    settleBuildinToggleSlotHeight(slot, false)
    expect(slot.style.height).toBe('0px')
    expect(slot.style.overflow).toBe('hidden')
    settleBuildinToggleSlotHeight(slot, true)
    expect(slot.style.height).toBe('')
    expect(slot.style.overflow).toBe('')
  })
})

describe('measureToggleSlotNaturalHeight', () => {
  it('не оставляет height:auto после замера', () => {
    const slot = document.createElement('div')
    slot.style.height = '0px'
    slot.style.overflow = 'hidden'
    measureToggleSlotNaturalHeight(slot)
    expect(slot.style.height).toBe('0px')
    expect(slot.style.overflow).toBe('hidden')
  })
})
