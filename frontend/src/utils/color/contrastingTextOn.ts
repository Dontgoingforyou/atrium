/** Тёмный текст на светлой заливке (теги, календарь). */
export const TEXT_ON_LIGHT_BG = '#252525'
/** Светлый текст на тёмной заливке; fallback при невалидном hex. */
export const TEXT_ON_DARK_BG = '#FFFFFF'

export function hexToRgb(hex: string): { r: number; g: number; b: number } | null {
  const raw = hex.trim().replace(/^#/, '')
  let normalized = raw
  if (/^[0-9a-fA-F]{3}$/.test(raw)) {
    normalized = `${raw[0]}${raw[0]}${raw[1]}${raw[1]}${raw[2]}${raw[2]}`
  }
  if (!/^[0-9a-fA-F]{6}$/.test(normalized)) return null
  return {
    r: parseInt(normalized.slice(0, 2), 16),
    g: parseInt(normalized.slice(2, 4), 16),
    b: parseInt(normalized.slice(4, 6), 16),
  }
}

function linearizeChannel(channel: number): number {
  const s = channel / 255
  return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4
}

/** Относительная яркость по WCAG 2.x. Невалидный hex → 0. */
export function relativeLuminance(hex: string): number {
  const rgb = hexToRgb(hex)
  if (!rgb) return 0
  const r = linearizeChannel(rgb.r)
  const g = linearizeChannel(rgb.g)
  const b = linearizeChannel(rgb.b)
  return 0.2126 * r + 0.7152 * g + 0.0722 * b
}

/** Контраст WCAG 2.x между двумя яркостями. */
export function contrastRatio(luminanceA: number, luminanceB: number): number {
  const lighter = Math.max(luminanceA, luminanceB)
  const darker = Math.min(luminanceA, luminanceB)
  return (lighter + 0.05) / (darker + 0.05)
}

/**
 * Текст на произвольной заливке: тёмный или белый — у кого выше contrast ratio.
 * При равенстве — тёмный (яркие жёлтые/янтарные читаются).
 */
export function contrastingTextOn(backgroundColor: string): string {
  if (!hexToRgb(backgroundColor)) return TEXT_ON_DARK_BG
  const bg = relativeLuminance(backgroundColor)
  const vsDark = contrastRatio(bg, relativeLuminance(TEXT_ON_LIGHT_BG))
  const vsLight = contrastRatio(bg, relativeLuminance(TEXT_ON_DARK_BG))
  return vsDark >= vsLight ? TEXT_ON_LIGHT_BG : TEXT_ON_DARK_BG
}
