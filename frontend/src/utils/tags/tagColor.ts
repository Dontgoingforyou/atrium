import type { ThemeId } from '../../store/themeStore'
import {
  contrastingTextOn,
  hexToRgb,
  relativeLuminance,
} from '../color/contrastingTextOn'

export { hexToRgb, relativeLuminance } from '../color/contrastingTextOn'

/** Тема для расчёта цветов: DOM (`data-theme`) приоритетнее store (до rehydration zustand). */
export function getEffectiveTheme(storeTheme: ThemeId): ThemeId {
  if (typeof document === 'undefined') return storeTheme
  const attr = document.documentElement.getAttribute('data-theme')
  return attr === 'dark' || attr === 'light' ? attr : storeTheme
}

const LIGHT_THEME_MAX_LUMINANCE = 0.45
const DARK_THEME_MIN_LUMINANCE = 0.28
/** Итерации бинарного поиска lightness до порога WCAG-яркости. */
const LIGHTNESS_SEARCH_STEPS = 24

const DEFAULT_COLOR_LIGHT = '#7C3AED'
const DEFAULT_COLOR_DARK = '#78B1C4'

/** Контрастный цвет чипа, если сохранённый плохо виден на теме зрителя. */
export const TAG_DISPLAY_FALLBACK_LIGHT = '#252525'
export const TAG_DISPLAY_FALLBACK_DARK = '#E6EDF3'

/** Контрастный цвет текста на заливке чипа (active) — WCAG contrast, не порог 0.5. */
export function getContrastingTagTextColor(backgroundColor: string): string {
  return contrastingTextOn(backgroundColor)
}

export function isTagColorAllowed(color: string, theme: ThemeId): boolean {
  const lum = relativeLuminance(color)
  if (theme === 'light') return lum <= LIGHT_THEME_MAX_LUMINANCE
  return lum >= DARK_THEME_MIN_LUMINANCE
}

function rgbToHsl(r: number, g: number, b: number): { h: number; s: number; l: number } {
  const rn = r / 255
  const gn = g / 255
  const bn = b / 255
  const max = Math.max(rn, gn, bn)
  const min = Math.min(rn, gn, bn)
  const l = (max + min) / 2
  if (max === min) return { h: 0, s: 0, l }

  const d = max - min
  const s = l > 0.5 ? d / (2 - max - min) : d / (max + min)
  let h = 0
  if (max === rn) h = ((gn - bn) / d + (gn < bn ? 6 : 0)) / 6
  else if (max === gn) h = ((bn - rn) / d + 2) / 6
  else h = ((rn - gn) / d + 4) / 6
  return { h, s, l }
}

function hueToRgbChannel(p: number, q: number, t: number): number {
  let tt = t
  if (tt < 0) tt += 1
  if (tt > 1) tt -= 1
  if (tt < 1 / 6) return p + (q - p) * 6 * tt
  if (tt < 1 / 2) return q
  if (tt < 2 / 3) return p + (q - p) * (2 / 3 - tt) * 6
  return p
}

function hslToRgb(h: number, s: number, l: number): { r: number; g: number; b: number } {
  if (s === 0) {
    const v = Math.round(l * 255)
    return { r: v, g: v, b: v }
  }
  const q = l < 0.5 ? l * (1 + s) : l + s - l * s
  const p = 2 * l - q
  return {
    r: Math.round(hueToRgbChannel(p, q, h + 1 / 3) * 255),
    g: Math.round(hueToRgbChannel(p, q, h) * 255),
    b: Math.round(hueToRgbChannel(p, q, h - 1 / 3) * 255),
  }
}

function channelToHex(channel: number): string {
  return Math.max(0, Math.min(255, channel)).toString(16).padStart(2, '0').toUpperCase()
}

function rgbToHex(r: number, g: number, b: number): string {
  return `#${channelToHex(r)}${channelToHex(g)}${channelToHex(b)}`
}

function adjustTagColorLightness(color: string, theme: ThemeId): string {
  const rgb = hexToRgb(color)
  if (!rgb) {
    return theme === 'light' ? TAG_DISPLAY_FALLBACK_LIGHT : TAG_DISPLAY_FALLBACK_DARK
  }

  const { h, s, l } = rgbToHsl(rgb.r, rgb.g, rgb.b)
  let lo = theme === 'light' ? 0 : l
  let hi = theme === 'light' ? l : 1
  let best = theme === 'light' ? TAG_DISPLAY_FALLBACK_LIGHT : TAG_DISPLAY_FALLBACK_DARK

  for (let step = 0; step < LIGHTNESS_SEARCH_STEPS; step += 1) {
    const mid = (lo + hi) / 2
    const adjustedRgb = hslToRgb(h, s, mid)
    const candidateHex = rgbToHex(adjustedRgb.r, adjustedRgb.g, adjustedRgb.b)

    if (theme === 'light') {
      if (relativeLuminance(candidateHex) <= LIGHT_THEME_MAX_LUMINANCE) {
        best = candidateHex
        lo = mid
      } else {
        hi = mid
      }
    } else if (relativeLuminance(candidateHex) >= DARK_THEME_MIN_LUMINANCE) {
      best = candidateHex
      hi = mid
    } else {
      lo = mid
    }
  }

  return best
}

/**
 * Цвет для отображения чипа у зрителя с данной темой.
 * Сохранённый цвет в БД не меняется — только подстройка lightness при плохой контрастности.
 */
export function getTagDisplayColor(color: string, theme: ThemeId): string {
  if (!hexToRgb(color)) {
    return theme === 'light' ? TAG_DISPLAY_FALLBACK_LIGHT : TAG_DISPLAY_FALLBACK_DARK
  }
  if (isTagColorAllowed(color, theme)) return color.toUpperCase()
  return adjustTagColorLightness(color, theme)
}

export type TagChipBorderVariant = 'default' | 'soft'

export function getTagChipStyle(
  storedColor: string,
  theme: ThemeId,
  opts?: { active?: boolean; border?: TagChipBorderVariant },
): { backgroundColor: string; color: string; borderColor: string } {
  const display = getTagDisplayColor(storedColor, theme)
  if (opts?.active) {
    return {
      backgroundColor: display,
      color: getContrastingTagTextColor(display),
      borderColor: display,
    }
  }
  const borderColor = opts?.border === 'soft' ? `${display}55` : display
  return {
    backgroundColor: `${display}22`,
    color: display,
    borderColor,
  }
}

export function getDefaultTagColor(theme: ThemeId): string {
  return theme === 'light' ? DEFAULT_COLOR_LIGHT : DEFAULT_COLOR_DARK
}

export function getTagColorValidationMessage(theme: ThemeId): string {
  return theme === 'light'
    ? 'Для светлой темы выберите более тёмный цвет — иначе тег будет плохо виден.'
    : 'Для тёмной темы выберите более светлый цвет — иначе тег будет плохо виден.'
}

/** Проверка цвета перед отправкой на API (swatch quick-edit и submit). */
export function validateTagColorForTheme(color: string, theme: ThemeId): string | null {
  if (isTagColorAllowed(color, theme)) return null
  return getTagColorValidationMessage(theme)
}
