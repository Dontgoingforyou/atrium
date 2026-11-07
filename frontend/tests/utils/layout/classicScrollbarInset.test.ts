import { describe, expect, it } from 'vitest'

import {
  CLASSIC_SCROLLBAR_INSET_VAR,
  applyClassicScrollbarInsetVar,
  classicScrollbarInsetCssValue,
  classicScrollbarInsetPx,
} from '@/utils/layout/classicScrollbarInset'

function contentWidthAfterInset(
  offsetWidth: number,
  clientWidth: number,
  paddingLeft: number,
  paddingRight: number,
): number {
  const inset = classicScrollbarInsetPx(offsetWidth, clientWidth)
  return clientWidth - paddingLeft - (paddingRight - inset)
}

describe('classicScrollbarInsetPx', () => {
  it('без полосы (overlay или контент короче) — inset 0', () => {
    expect(classicScrollbarInsetPx(800, 800)).toBe(0)
  })

  it('классический скроллбар 15px — inset равен забранной ширине', () => {
    expect(classicScrollbarInsetPx(800, 785)).toBe(15)
  })

  it('некорректные размеры — 0, без отрицательного inset', () => {
    expect(classicScrollbarInsetPx(800, 900)).toBe(0)
    expect(classicScrollbarInsetPx(Number.NaN, 800)).toBe(0)
  })
})

describe('ширина колонки контента', () => {
  const pad = 32

  it('с полосой и без неё совпадает: скроллбар садится в padding, не сдвигает текст', () => {
    const withoutBar = contentWidthAfterInset(800, 800, pad, pad)
    const withBar = contentWidthAfterInset(800, 785, pad, pad)
    expect(withoutBar).toBe(736)
    expect(withBar).toBe(withoutBar)
  })
})

describe('classicScrollbarInsetCssValue / applyClassicScrollbarInsetVar', () => {
  it('0 — не пишем переменную (нет пустого gutter)', () => {
    expect(classicScrollbarInsetCssValue(0)).toBeNull()
    const calls: string[] = []
    applyClassicScrollbarInsetVar(
      {
        setProperty: () => {
          calls.push('set')
        },
        removeProperty: (name) => {
          calls.push(`remove:${name}`)
        },
      },
      0,
    )
    expect(calls).toEqual([`remove:${CLASSIC_SCROLLBAR_INSET_VAR}`])
  })

  it('положительный inset — CSS-пиксели в переменную', () => {
    expect(classicScrollbarInsetCssValue(15)).toBe('15px')
    const set: Array<[string, string]> = []
    applyClassicScrollbarInsetVar(
      {
        setProperty: (name, value) => {
          set.push([name, value])
        },
        removeProperty: () => {
          set.push(['remove', ''])
        },
      },
      15,
    )
    expect(set).toEqual([[CLASSIC_SCROLLBAR_INSET_VAR, '15px']])
  })
})
