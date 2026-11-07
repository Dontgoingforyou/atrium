// @vitest-environment jsdom

import { describe, expect, it, vi } from 'vitest'

import { computeMentionDropdownCoords } from '../../../src/utils/chat/mentionDropdownLayout'

describe('computeMentionDropdownCoords', () => {
  it('предпочитает размещение сверху, если места достаточно', () => {
    vi.spyOn(window, 'innerWidth', 'get').mockReturnValue(1024)
    vi.spyOn(window, 'innerHeight', 'get').mockReturnValue(800)
    const textarea = document.createElement('textarea')
    const dropdown = document.createElement('div')
    vi.spyOn(textarea, 'getBoundingClientRect').mockReturnValue({
      top: 400,
      bottom: 440,
      left: 50,
      width: 300,
      height: 40,
      right: 350,
      x: 50,
      y: 400,
      toJSON: () => ({}),
    })
    vi.spyOn(dropdown, 'getBoundingClientRect').mockReturnValue({
      top: 0,
      bottom: 120,
      left: 0,
      width: 200,
      height: 120,
      right: 200,
      x: 0,
      y: 0,
      toJSON: () => ({}),
    })

    const coords = computeMentionDropdownCoords(textarea, dropdown, 6)
    expect(coords.left).toBe(50)
    expect(coords.minWidth).toBe(300)
    expect(coords.top).toBe(400 - 120 - 6)
  })

  it('клампит left у правого края', () => {
    vi.spyOn(window, 'innerWidth', 'get').mockReturnValue(400)
    vi.spyOn(window, 'innerHeight', 'get').mockReturnValue(800)
    const textarea = document.createElement('textarea')
    const dropdown = document.createElement('div')
    vi.spyOn(textarea, 'getBoundingClientRect').mockReturnValue({
      top: 200,
      bottom: 240,
      left: 250,
      width: 200,
      height: 40,
      right: 450,
      x: 250,
      y: 200,
      toJSON: () => ({}),
    })
    vi.spyOn(dropdown, 'getBoundingClientRect').mockReturnValue({
      top: 0,
      bottom: 80,
      left: 0,
      width: 200,
      height: 80,
      right: 200,
      x: 0,
      y: 0,
      toJSON: () => ({}),
    })
    const coords = computeMentionDropdownCoords(textarea, dropdown, 6)
    expect(coords.minWidth).toBe(200)
    expect(coords.left).toBe(400 - 200 - 8)
  })
})
