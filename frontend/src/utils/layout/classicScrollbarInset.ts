/** CSS-переменная на скролл-контейнере: сколько px забрал классический скроллбар. */
export const CLASSIC_SCROLLBAR_INSET_VAR = '--classic-scrollbar-inset'

/** Ширина полосы, которую классический скроллбар вычел из clientWidth. Overlay → 0. */
export function classicScrollbarInsetPx(offsetWidth: number, clientWidth: number): number {
  const taken = offsetWidth - clientWidth
  if (!Number.isFinite(taken) || taken <= 0) {
    return 0
  }
  return Math.round(taken)
}

export function classicScrollbarInsetCssValue(insetPx: number): string | null {
  if (insetPx <= 0) {
    return null
  }
  return `${insetPx}px`
}

type StyleVarWriter = {
  setProperty: (name: string, value: string) => void
  removeProperty: (name: string) => void
}

export function applyClassicScrollbarInsetVar(style: StyleVarWriter, insetPx: number): void {
  const css = classicScrollbarInsetCssValue(insetPx)
  if (css === null) {
    style.removeProperty(CLASSIC_SCROLLBAR_INSET_VAR)
    return
  }
  style.setProperty(CLASSIC_SCROLLBAR_INSET_VAR, css)
}
