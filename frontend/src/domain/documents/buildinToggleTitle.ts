import { toggleBodyContentEditable } from './buildinToggleSelection'

export { isCaretInsideNode } from './buildinToggleSelection'

/** Разбор и синхронизация заголовка buildin-toggle (attrs.title vs NodeView input). */

export function normalizeBuildinToggleTitle(value: string): string {
  return normalizeBuildinToggleTitleLive(value).trim()
}

/** Во время набора не trim — пробел в конце иначе схлопывается на каждый символ. */
export function normalizeBuildinToggleTitleLive(value: string): string {
  return value.replace(/\u00a0/g, ' ')
}

/** preventDefault на input внутри summary ломает каретку (Safari / тачпад). */
export function shouldPreventDefaultOnToggleTitleClick(): boolean {
  return false
}

export function isToggleTitleSpaceKey(key: string): boolean {
  return key === ' ' || key === 'Spacebar'
}

/** Space в input внутри summary тоглит details и отдаёт каретку в тело блока. */
export function shouldPreventDefaultOnToggleTitleKey(key: string): boolean {
  return isToggleTitleSpaceKey(key)
}

export function isBuildinToggleTitleInputTarget(target: EventTarget | null): boolean {
  return target instanceof Element && Boolean(target.closest('.buildin-toggle-title-input'))
}

export function isBuildinToggleArrowTarget(target: EventTarget | null): boolean {
  return target instanceof Element && Boolean(target.closest('.buildin-toggle-arrow'))
}


export function shouldToggleBuildinOpenOnChromeClick(target: EventTarget | null): boolean {
  if (!(target instanceof Element)) return false
  if (target.closest('.buildin-toggle-delete')) return false
  if (isBuildinToggleTitleInputTarget(target)) return false
  return isBuildinToggleArrowTarget(target) || Boolean(target.closest('.buildin-toggle-header'))
}

/** Инвертирует визуальный open; native details.open в редакторе больше не источник. */
export function invertBuildinToggleOpen(attrsOpen: boolean): boolean {
  return !attrsOpen
}

/** Первая текстовая позиция в теле: +1 вход в toggle, +1 вход в абзац. */
export function resolveBuildinToggleBodyCaretPos(togglePos: number, nodeSize: number): number | null {
  if (nodeSize < 4) return null
  return togglePos + 2
}

export function emptyParagraphAfterToggleRange(params: {
  togglePos: number
  toggleSize: number
  nextTypeName: string | null
  nextNodeSize: number
  nextEmpty: boolean
}): { from: number; to: number } | null {
  if (params.nextTypeName !== 'paragraph' || !params.nextEmpty) return null
  const from = params.togglePos + params.toggleSize
  return { from, to: from + params.nextNodeSize }
}

export function buildinToggleAttrsOnTitleEnter<T extends { open?: boolean; title?: string }>(
  attrs: T,
  title: string,
): T {
  return { ...attrs, title, open: true }
}

export function insertPlainTextAtSelection(
  value: string,
  selectionStart: number,
  selectionEnd: number,
  text: string,
): { value: string; caret: number } {
  const start = Math.max(0, Math.min(selectionStart, value.length))
  const end = Math.max(start, Math.min(selectionEnd, value.length))
  return {
    value: `${value.slice(0, start)}${text}${value.slice(end)}`,
    caret: start + text.length,
  }
}

export function parseBuildinToggleTitleFromParts(params: {
  summaryVisibleText: string
  detailsTitleAttr: string | null | undefined
}): string {
  const fromSummary = normalizeBuildinToggleTitle(params.summaryVisibleText)
  if (fromSummary) return fromSummary
  return normalizeBuildinToggleTitle(params.detailsTitleAttr ?? '')
}

/** Chrome NodeView в summary; тот же селектор — в document-collab parse-buildin-toggle-title.mjs. */
export const BUILDIN_TOGGLE_TITLE_CHROME_SELECTOR = 'input, button, .buildin-toggle-arrow'

/** Текст summary без chrome NodeView (стрелка, input, кнопка удаления). */
export function extractSummaryVisibleText(summary: Element): string {
  const clone = summary.cloneNode(true) as Element
  clone.querySelectorAll(BUILDIN_TOGGLE_TITLE_CHROME_SELECTOR).forEach((el) => el.remove())
  return clone.textContent ?? ''
}

export function parseBuildinToggleTitle(element: Element): string {
  const summary = element.querySelector('summary')
  const summaryVisibleText = summary ? extractSummaryVisibleText(summary) : ''
  return parseBuildinToggleTitleFromParts({
    summaryVisibleText,
    detailsTitleAttr: element.getAttribute('title'),
  })
}

export function shouldApplyRemoteToggleTitle(params: {
  inputValue: string
  attrsTitle: string
  isInputFocused: boolean
  isLocallyDirty: boolean
}): boolean {
  if (params.isInputFocused || params.isLocallyDirty) return false
  return params.inputValue !== params.attrsTitle
}

export function applyBuildinToggleEditChrome(
  titleInput: { readOnly: boolean; tabIndex: number },
  deleteBtn: { hidden: boolean; disabled: boolean },
  editable: boolean,
  contentDOM?: { contentEditable: string },
): void {
  titleInput.readOnly = !editable
  titleInput.tabIndex = editable ? 0 : -1
  deleteBtn.hidden = !editable
  deleteBtn.disabled = !editable
  if (contentDOM) {
    contentDOM.contentEditable = toggleBodyContentEditable(editable)
  }
}
