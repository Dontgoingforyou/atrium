import { describe, expect, it } from 'vitest'

import { shouldHoldOutsideCloseUntilPointerUp } from '@/domain/documents/documentBodyEditGesture'

describe('shouldHoldOutsideCloseUntilPointerUp', () => {
  it('после входа по click не глушит первый outside — иначе выход со второго клика', () => {
    expect(shouldHoldOutsideCloseUntilPointerUp('click')).toBe(false)
  })

  it('после входа по pointerdown держит outside до конца жеста', () => {
    expect(shouldHoldOutsideCloseUntilPointerUp('pointerdown')).toBe(true)
  })
})
