import { describe, expect, it } from 'vitest'

import {
  TEXT_ON_DARK_BG,
  TEXT_ON_LIGHT_BG,
  contrastingTextOn,
  relativeLuminance,
} from '@/utils/color/contrastingTextOn'

describe('contrastingTextOn', () => {
  it('на бледном и насыщенном жёлтом / янтаре / лайме — тёмный текст', () => {
    const brightHues = ['#FFF4B0', '#FACC15', '#EAB308', '#F59E0B', '#84CC16']
    for (const hex of brightHues) {
      expect(contrastingTextOn(hex), hex).toBe(TEXT_ON_LIGHT_BG)
    }
  })

  it('на белом и #fff — тёмный текст', () => {
    expect(contrastingTextOn('#FFFFFF')).toBe(TEXT_ON_LIGHT_BG)
    expect(contrastingTextOn('#fff')).toBe(TEXT_ON_LIGHT_BG)
  })

  it('на тёмном и дефолтном фиолетовом календаря — светлый текст', () => {
    expect(contrastingTextOn('#252525')).toBe(TEXT_ON_DARK_BG)
    expect(contrastingTextOn('#8B5CF6')).toBe(TEXT_ON_DARK_BG)
  })

  it('на tailwind-синем #3B82F6 тёмный текст контрастнее белого', () => {
    expect(contrastingTextOn('#3B82F6')).toBe(TEXT_ON_LIGHT_BG)
  })

  it('невалидный hex — светлый fallback', () => {
    expect(contrastingTextOn('not-a-color')).toBe(TEXT_ON_DARK_BG)
    expect(contrastingTextOn('')).toBe(TEXT_ON_DARK_BG)
    expect(contrastingTextOn('#12')).toBe(TEXT_ON_DARK_BG)
  })
})

describe('relativeLuminance', () => {
  it('белый ≈ 1, чёрный ≈ 0', () => {
    expect(relativeLuminance('#FFFFFF')).toBeCloseTo(1, 2)
    expect(relativeLuminance('#000000')).toBeCloseTo(0, 2)
  })
})
