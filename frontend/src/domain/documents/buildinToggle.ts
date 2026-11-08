/**
 * Логика авто-раскрытия buildin-toggle (details.buildin-toggle) в HTML просмотра
 * документа и rich-text редактора задач. Вынесено из taskDetailPanelContent.ts,
 * чтобы не смешивать ответственность «контент панели задачи» и «манипуляция HTML
 * toggle-блоков» (, SRP).
 *
 * Проверку «есть ли видимый контент в toggle-body» переиспользуем из
 * utils/html/isEmptyHtml.ts (единый атом buildinToggleBodyHasVisibleContent) —.
 */
import { buildinToggleBodyHasVisibleContent } from '../../utils/html/isEmptyHtml'

export const buildinToggleBodyHasContent = buildinToggleBodyHasVisibleContent

/** Новый блок сразу раскрыт; свернуть — стрелкой, не через Enter. */
export function buildinToggleInsertAttrs(): { title: string; open: boolean } {
  return { title: 'Новый раздел', open: true }
}

/** Слот тела: data-state для стрелки; высота — settle/play в buildinToggleSlotAnim, не CSS grid. */
export function buildinToggleBodySlotState(open: boolean): 'open' | 'closed' {
  return open ? 'open' : 'closed'
}

export function buildinToggleExpandedDataset(open: boolean): 'true' | 'false' {
  return open ? 'true' : 'false'
}

/** Совпадает с transition `.taskPanelBodyShell` (комментарии задачи). */
export const BUILDIN_TOGGLE_BODY_ANIM_MS = 250
export const BUILDIN_TOGGLE_BODY_EASE = 'ease'

export function buildinToggleBodyAnimMs(): number {
  if (typeof matchMedia !== 'undefined' && matchMedia('(prefers-reduced-motion: reduce)').matches) {
    return 0
  }
  return BUILDIN_TOGGLE_BODY_ANIM_MS
}

/** И раскрытие, и сворачивание: attrs.open только после анимации, иначе Yjs сносит NodeView. */
export function buildinToggleOpenCommitDelayMs(): number {
  return buildinToggleBodyAnimMs()
}

/** Пока слот анимируется, attrs.open ещё старый — не откатывать data-state. */
export function shouldHoldToggleVisualOpen(
  pendingOpen: boolean | null,
  attrsOpen: boolean,
): boolean {
  return pendingOpen !== null && pendingOpen !== attrsOpen
}

/**
 * Settle высоты слота только при смене open.
 * На каждый Enter/набор settle сбрасывает height и каретка остаётся на старой строке.
 */
export function shouldSettleToggleChromeOnNodeUpdate(params: {
  pendingOpen: boolean | null
  prevOpen: boolean
  nextOpen: boolean
}): boolean {
  if (shouldHoldToggleVisualOpen(params.pendingOpen, params.nextOpen)) {
    return false
  }
  return params.prevOpen !== params.nextOpen
}

/**
 * Открытый слот: снять залипший inline height без полного settle
 * (settle на набор ломает каретку; залипший px раздувает пустой ящик).
 */
export function shouldReleaseOpenToggleSlotHeight(params: {
  isOpen: boolean
  hasInlineHeight: boolean
  isHoldingVisual: boolean
}): boolean {
  return params.isOpen && params.hasInlineHeight && !params.isHoldingVisual
}

/** Мутации шапки/слота — не контент ProseMirror; иначе PM сносит NodeView на каждом кадре height. */
export function shouldIgnoreBuildinToggleChromeMutation(
  target: EventTarget | null,
  contentDOM: Node,
): boolean {
  if (!(target instanceof Node)) return false
  return target !== contentDOM && !contentDOM.contains(target)
}

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
