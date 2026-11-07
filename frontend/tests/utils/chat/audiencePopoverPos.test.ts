// @vitest-environment jsdom

import { describe, expect, it, vi } from 'vitest'

import { audiencePopoverStyle } from '@/utils/chat/audiencePopoverPos'

describe('audiencePopoverStyle', () => {
  it('ставит попап выше якоря в нижней половине экрана', () => {
    vi.spyOn(window, 'innerWidth', 'get').mockReturnValue(800)
    vi.spyOn(window, 'innerHeight', 'get').mockReturnValue(800)
    const style = audiencePopoverStyle({ top: 500, bottom: 520, left: 100, right: 140 }, 220)
    expect(style.transform).toBe('translateY(-100%)')
    expect(style.top).toBe(494)
    expect(style.width).toBe(220)
  })

  it('не уводит попап за верх, если якорь слишком высоко', () => {
    vi.spyOn(window, 'innerWidth', 'get').mockReturnValue(800)
    vi.spyOn(window, 'innerHeight', 'get').mockReturnValue(800)
    const style = audiencePopoverStyle({ top: 10, bottom: 500, left: 100, right: 140 }, 220)
    expect(style.transform).toBeUndefined()
    expect(style.top).toBe(506)
  })
})
