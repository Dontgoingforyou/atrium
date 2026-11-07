/** Размещение выпадающего списка @упоминаний: предпочтительно над полем ввода. */

export type MentionDropdownCoords = {
  top: number
  left: number
  minWidth: number
}

export function computeMentionDropdownCoords(
  textarea: HTMLTextAreaElement,
  dropdownEl: HTMLElement,
  gap = 6,
): MentionDropdownCoords {
  const r = textarea.getBoundingClientRect()
  const h = dropdownEl.getBoundingClientRect().height
  const margin = 8
  const vw = window.innerWidth
  const minWidth = Math.min(Math.max(200, r.width), Math.max(0, vw - margin * 2))
  const spaceAbove = r.top
  const spaceBelow = window.innerHeight - r.bottom
  const preferAbove = spaceAbove >= h + gap || spaceAbove > spaceBelow
  let top = preferAbove ? r.top - h - gap : r.bottom + gap
  const maxTop = window.innerHeight - h - margin
  const minTop = margin
  top = Math.min(Math.max(minTop, top), maxTop)
  const maxLeft = Math.max(margin, vw - minWidth - margin)
  const left = Math.min(Math.max(margin, r.left), maxLeft)
  return { top, left, minWidth }
}
