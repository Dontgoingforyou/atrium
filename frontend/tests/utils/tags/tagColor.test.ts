// @vitest-environment jsdom
import { afterEach, describe, expect, it } from 'vitest'
import {
  getContrastingTagTextColor,
  getDefaultTagColor,
  getEffectiveTheme,
  getTagChipStyle,
  getTagDisplayColor,
  getTagColorValidationMessage,
  isTagColorAllowed,
  relativeLuminance,
  TAG_DISPLAY_FALLBACK_DARK,
  TAG_DISPLAY_FALLBACK_LIGHT,
} from '@/utils/tags/tagColor'

describe('getEffectiveTheme', () => {
  afterEach(() => {
    document.documentElement.removeAttribute('data-theme')
  })

  it('возвращает data-theme при рассинхроне со store', () => {
    document.documentElement.setAttribute('data-theme', 'dark')
    expect(getEffectiveTheme('light')).toBe('dark')
  })

  it('использует storeTheme если data-theme не задан', () => {
    expect(getEffectiveTheme('dark')).toBe('dark')
  })
})

describe('getTagDisplayColor с effective theme', () => {
  afterEach(() => {
    document.documentElement.removeAttribute('data-theme')
  })

  it('яркий жёлтый не подменяется на тёмный fallback при DOM dark и store light', () => {
    document.documentElement.setAttribute('data-theme', 'dark')
    const theme = getEffectiveTheme('light')
    expect(getTagDisplayColor('#FACC15', theme)).toBe('#FACC15')
    expect(getTagDisplayColor('#FACC15', theme)).not.toBe(TAG_DISPLAY_FALLBACK_LIGHT)
  })

  it('active-стиль жёлтого тега сохраняет заливку при effective dark', () => {
    document.documentElement.setAttribute('data-theme', 'dark')
    const theme = getEffectiveTheme('light')
    const style = getTagChipStyle('#FACC15', theme, { active: true })
    expect(style.backgroundColor).toBe('#FACC15')
  })
})

describe('relativeLuminance', () => {
  it('возвращает 1 для белого', () => {
    expect(relativeLuminance('#FFFFFF')).toBeCloseTo(1, 2)
  })

  it('возвращает 0 для чёрного', () => {
    expect(relativeLuminance('#000000')).toBeCloseTo(0, 2)
  })
})

describe('isTagColorAllowed', () => {
  it('отклоняет белый на светлой теме', () => {
    expect(isTagColorAllowed('#FFFFFF', 'light')).toBe(false)
  })

  it('отклоняет чёрный на тёмной теме', () => {
    expect(isTagColorAllowed('#111111', 'dark')).toBe(false)
  })

  it('принимает синий на светлой теме', () => {
    expect(isTagColorAllowed('#3B82F6', 'light')).toBe(true)
  })

  it('принимает белый на тёмной теме', () => {
    expect(isTagColorAllowed('#FFFFFF', 'dark')).toBe(true)
  })

  it('принимает голубой на тёмной теме', () => {
    expect(isTagColorAllowed('#78B1C4', 'dark')).toBe(true)
  })

  it('принимает достаточно яркие цвета каталога на тёмной теме', () => {
    expect(isTagColorAllowed('#F97316', 'dark')).toBe(true)
    expect(isTagColorAllowed('#78B1C4', 'dark')).toBe(true)
  })

  it('отклоняет слишком тёмные цвета каталога на тёмной теме', () => {
    expect(isTagColorAllowed('#3B82F6', 'dark')).toBe(false)
    expect(isTagColorAllowed('#EF4444', 'dark')).toBe(false)
    expect(isTagColorAllowed('#035EBF', 'dark')).toBe(false)
    expect(isTagColorAllowed('#791A3E', 'dark')).toBe(false)
  })

  it('отклоняет почти чёрный на тёмной теме', () => {
    expect(isTagColorAllowed('#252525', 'dark')).toBe(false)
  })
})

describe('getDefaultTagColor', () => {
  it('возвращает тёмный цвет для светлой темы', () => {
    expect(isTagColorAllowed(getDefaultTagColor('light'), 'light')).toBe(true)
  })

  it('возвращает светлый цвет для тёмной темы', () => {
    expect(isTagColorAllowed(getDefaultTagColor('dark'), 'dark')).toBe(true)
  })
})

describe('getTagDisplayColor', () => {
  it('оставляет допустимый синий на светлой теме без изменений', () => {
    expect(getTagDisplayColor('#3B82F6', 'light')).toBe('#3B82F6')
  })

  it('оставляет белый на тёмной теме без изменений', () => {
    expect(getTagDisplayColor('#FFFFFF', 'dark')).toBe('#FFFFFF')
  })

  it('затемняет слишком светлый цвет на светлой теме до допустимой яркости', () => {
    const display = getTagDisplayColor('#FFFFFF', 'light')
    expect(display).not.toBe('#FFFFFF')
    expect(isTagColorAllowed(display, 'light')).toBe(true)
    expect(relativeLuminance(display)).toBeLessThanOrEqual(0.45)
  })

  it('осветляет слишком тёмный цвет на тёмной теме до допустимой яркости', () => {
    const display = getTagDisplayColor('#000000', 'dark')
    expect(display).not.toBe('#000000')
    expect(isTagColorAllowed(display, 'dark')).toBe(true)
    expect(relativeLuminance(display)).toBeGreaterThanOrEqual(0.28)
  })

  it('осветляет тёмный каталожный цвет на тёмной теме', () => {
    const display = getTagDisplayColor('#791A3E', 'dark')
    expect(display).not.toBe('#791A3E')
    expect(isTagColorAllowed(display, 'dark')).toBe(true)
    expect(relativeLuminance(display)).toBeGreaterThanOrEqual(0.28)
  })

  it('сохраняет отличимость разных светлых оттенков после затемнения на светлой теме', () => {
    const fromWhite = getTagDisplayColor('#FFFFFF', 'light')
    const fromMint = getTagDisplayColor('#CCE8B5', 'light')
    expect(fromWhite).not.toBe(fromMint)
    expect(isTagColorAllowed(fromWhite, 'light')).toBe(true)
    expect(isTagColorAllowed(fromMint, 'light')).toBe(true)
  })

  it('сохраняет отличимость разных тёмных оттенков после осветления на тёмной теме', () => {
    const fromBlack = getTagDisplayColor('#000000', 'dark')
    const fromBrown = getTagDisplayColor('#583400', 'dark')
    expect(fromBlack).not.toBe(fromBrown)
    expect(isTagColorAllowed(fromBlack, 'dark')).toBe(true)
    expect(isTagColorAllowed(fromBrown, 'dark')).toBe(true)
  })

  it('для невалидного hex возвращает fallback темы', () => {
    expect(getTagDisplayColor('not-a-color', 'light')).toBe(TAG_DISPLAY_FALLBACK_LIGHT)
    expect(getTagDisplayColor('zzzzzz', 'dark')).toBe(TAG_DISPLAY_FALLBACK_DARK)
  })
})

describe('getContrastingTagTextColor', () => {
  it('тёмный текст на светлом фоне', () => {
    expect(getContrastingTagTextColor('#FFFFFF')).toBe('#252525')
  })

  it('светлый текст на тёмном фоне', () => {
    expect(getContrastingTagTextColor('#252525')).toBe('#FFFFFF')
  })

  it('тёмный текст на янтарном, который ломал порог 0.5', () => {
    expect(getContrastingTagTextColor('#EAB308')).toBe('#252525')
  })
})

describe('getTagChipStyle', () => {
  it('active: контрастный текст на белой заливке в тёмной теме', () => {
    const style = getTagChipStyle('#FFFFFF', 'dark', { active: true })
    expect(style.backgroundColor).toBe('#FFFFFF')
    expect(style.color).toBe('#252525')
  })

  it('active: светлый текст на затемнённой заливке в светлой теме', () => {
    const style = getTagChipStyle('#FFFFFF', 'light', { active: true })
    expect(isTagColorAllowed(style.backgroundColor, 'light')).toBe(true)
    expect(style.backgroundColor).not.toBe('#FFFFFF')
    expect(style.color).toBe(getContrastingTagTextColor(style.backgroundColor))
  })

  it('inactive: цвет текста совпадает с display', () => {
    const style = getTagChipStyle('#3B82F6', 'light', { active: false })
    expect(style.color).toBe('#3B82F6')
  })

  it('active: тёмный текст на янтарной заливке', () => {
    const style = getTagChipStyle('#EAB308', 'dark', { active: true })
    expect(style.backgroundColor).toBe('#EAB308')
    expect(style.color).toBe('#252525')
  })
})

describe('getTagColorValidationMessage', () => {
  it('возвращает текст для светлой темы', () => {
    expect(getTagColorValidationMessage('light')).toMatch(/тёмн/i)
  })

  it('возвращает текст для тёмной темы', () => {
    expect(getTagColorValidationMessage('dark')).toMatch(/светл/i)
  })
})
