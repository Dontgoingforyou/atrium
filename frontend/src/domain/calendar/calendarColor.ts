/** Дефолтный цвет календаря/события (runtime-значение для API, не CSS-токен). */
export const DEFAULT_CALENDAR_COLOR = '#8B5CF6'

const HEX6_RE = /^#[0-9A-Fa-f]{6}$/
const HEX3_RE = /^#[0-9A-Fa-f]{3}$/

/** Привести произвольную цветовую строку к значению `<input type="color">` (#rrggbb). */
export function toColorInputValue(color: string): string {
  const c = color.trim()
  if (HEX6_RE.test(c)) return c
  if (HEX3_RE.test(c)) {
    const r = c[1]
    const g = c[2]
    const b = c[3]
    return `#${r}${r}${g}${g}${b}${b}`
  }
  return DEFAULT_CALENDAR_COLOR
}
