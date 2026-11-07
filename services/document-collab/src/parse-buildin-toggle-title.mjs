/**
 * Разбор заголовка buildin-toggle для HTML↔Y.Doc.
 * Селектор chrome обязан совпадать с BUILDIN_TOGGLE_TITLE_CHROME_SELECTOR
 * в frontend/src/domain/documents/buildinToggleTitle.ts (sync-тест).
 */
export const BUILDIN_TOGGLE_TITLE_CHROME_SELECTOR = 'input, button, .buildin-toggle-arrow'

export function parseBuildinToggleTitle(element) {
  const summary = element.querySelector?.('summary')
  let fromSummary = ''
  if (summary) {
    const clone = summary.cloneNode(true)
    clone.querySelectorAll?.(BUILDIN_TOGGLE_TITLE_CHROME_SELECTOR).forEach((el) => el.remove())
    fromSummary = String(clone.textContent || '')
      .replace(/\u00a0/g, ' ')
      .trim()
  }
  if (fromSummary) return fromSummary
  return String(element.getAttribute?.('title') || '')
    .replace(/\u00a0/g, ' ')
    .trim()
}
