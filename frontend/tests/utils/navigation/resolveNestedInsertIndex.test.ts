import { describe, expect, it } from 'vitest'

import {
  nestedSiblingOrderKey,
  resolveNestedInsertIndex,
} from '@/utils/navigation/resolveNestedInsertIndex'

describe('nestedSiblingOrderKey', () => {
  it('стабилен по id', () => {
    expect(nestedSiblingOrderKey(['a', 'b', 'c'])).toBe('a,b,c')
  })
})

describe('resolveNestedInsertIndex', () => {
  const ids = ['a', 'b', 'c']
  const rects: Record<string, { top: number; height: number }> = {
    a: { top: 0, height: 40 },
    b: { top: 40, height: 40 },
    c: { top: 80, height: 40 },
  }
  const getRect = (id: string) => rects[id]

  it('null если id нет или один элемент', () => {
    expect(resolveNestedInsertIndex(['only'], 'only', 10, getRect)).toBeNull()
    expect(resolveNestedInsertIndex(ids, 'missing', 10, getRect)).toBeNull()
  })

  it('null если pointer в той же «половине» что и текущая позиция', () => {
    // b на индексе 1; pointer в зоне b (середина 60) — безMoved [a,c], mid a=20 mid c=100
    // pointer 60 < 100 → targetInWithout=1 === fromIdx → null
    expect(resolveNestedInsertIndex(ids, 'b', 60, getRect)).toBeNull()
  })

  it('перенос вниз: a → перед c', () => {
    // without [b,c]; pointer над верхней половиной c (y=85) → target 1
    // fromIdx 0 → toIdx 1 → [b,a,c]
    expect(resolveNestedInsertIndex(ids, 'a', 85, getRect)).toBe(1)
  })

  it('перенос в конец: a → после c', () => {
    expect(resolveNestedInsertIndex(ids, 'a', 110, getRect)).toBe(2)
  })

  it('перенос вверх: c → перед a', () => {
    expect(resolveNestedInsertIndex(ids, 'c', 10, getRect)).toBe(0)
  })

  it('пропускает отсутствующий rect и height <= 0', () => {
    const sparseGetRect = (id: string) => {
      if (id === 'b') return { top: 40, height: 0 }
      if (id === 'c') return undefined
      return rects[id]
    }
    // withoutMoved [b,c] оба пропускаются → targetInWithout = 2, fromIdx a = 0
    expect(resolveNestedInsertIndex(ids, 'a', 50, sparseGetRect)).toBe(2)
  })
})
