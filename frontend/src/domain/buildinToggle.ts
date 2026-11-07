import { buildinToggleBodyHasVisibleContent } from '../utils/html/isEmptyHtml'

export const buildinToggleBodyHasContent = buildinToggleBodyHasVisibleContent

/** Проставляет атрибут open на details.buildin-toggle в HTML просмотра документа. */
export function applyBuildinToggleAutoOpen(html: string): string {
  if (!html.includes('buildin-toggle')) return html
  if (typeof DOMParser === 'undefined') return html

  const doc = new DOMParser().parseFromString(html, 'text/html')
  doc.querySelectorAll('details.buildin-toggle').forEach((details) => {
    const body = details.querySelector('.buildin-toggle-body')
    if (buildinToggleBodyHasContent(body)) {
      details.setAttribute('open', 'open')
    } else {
      details.removeAttribute('open')
    }
  })
  return doc.body.innerHTML
}
