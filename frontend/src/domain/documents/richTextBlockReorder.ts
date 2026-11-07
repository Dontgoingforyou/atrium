/** Порог сдвига мыши: отличить reorder от выделения. Абзац — как PM; шапка toggle — весь раздел; тело — строка внутри. */
export const BLOCK_REORDER_THRESHOLD_PX = 8

export const BLOCK_REORDER_HEADER_THRESHOLD_PX = 16

export const BLOCK_REORDER_EXEMPT_SELECTOR =
  'input, textarea, button, a, .buildin-toggle-title-input, .buildin-toggle-delete, .column-resize-handle, table, td, th, .tableWrapper'

export const BLOCK_REORDER_HANDLE_ATTR = 'data-block-reorder-handle'

export const BLOCK_REORDER_HANDLE_SELECTOR = `[${BLOCK_REORDER_HANDLE_ATTR}]`

export const BLOCK_REORDER_DROP_LINE_PX = 2

export type BlockRelRect = { top: number; left: number; height: number; width: number }

export type BlockReorderHandleVisibility = {
  /** Символы в блоке без крайних пробелов. */
  textLength: number
  /** Картинка / таблица / toggle — блок без обязательного текста. */
  isAtomicBlock: boolean
}

/** Ручка только у блока с текстом или у атомарного (не у пустой строки). */
export function shouldShowBlockReorderHandle(input: BlockReorderHandleVisibility): boolean {
  if (input.isAtomicBlock) return true
  return input.textLength >= 1
}

export const BLOCK_REORDER_ATOMIC_NODE_NAMES = new Set(['documentImage', 'table', 'buildinToggle'])

export function isAtomicReorderBlock(nodeName: string): boolean {
  return BLOCK_REORDER_ATOMIC_NODE_NAMES.has(nodeName)
}

export type BlockReorderGestureOrigin = 'handle' | 'toggle-header' | 'text'

export type BlockReorderStartOptions = {
  threshold?: number
  origin?: BlockReorderGestureOrigin
}

export function resolveBlockReorderGestureOrigin(
  fromHandle: boolean,
  fromToggleHeader = false,
): BlockReorderGestureOrigin {
  if (fromHandle) return 'handle'
  if (fromToggleHeader) return 'toggle-header'
  return 'text'
}

export function canBeginBlockReorderGesture(origin: BlockReorderGestureOrigin): boolean {
  return origin === 'handle' || origin === 'toggle-header'
}

/** Тачпад после DnD часто шлёт лишний click — не снимать каретку и не тоглить details. */
export function shouldSuppressClickAfterBlockReorder(didActiveReorder: boolean): boolean {
  return didActiveReorder
}

export function shouldStartBlockReorder(
  dx: number,
  dy: number,
  thresholdOrOptions: number | BlockReorderStartOptions = BLOCK_REORDER_THRESHOLD_PX,
): boolean {
  const options: BlockReorderStartOptions =
    typeof thresholdOrOptions === 'number' ? { threshold: thresholdOrOptions } : thresholdOrOptions
  const origin = options.origin ?? 'handle'
  if (origin === 'text') return false
  const threshold =
    options.threshold ??
    (origin === 'toggle-header' ? BLOCK_REORDER_HEADER_THRESHOLD_PX : BLOCK_REORDER_THRESHOLD_PX)
  if (Math.hypot(dx, dy) < threshold) return false
  return Math.abs(dy) >= Math.abs(dx)
}

export function mappedInsertPosAfterDelete(insertPos: number, dragFrom: number, dragSize: number): number {
  if (dragFrom < insertPos) return insertPos - dragSize
  return insertPos
}

export function isSameBlockDrop(insertPos: number, dragFrom: number, dragTo: number): boolean {
  return insertPos === dragFrom || insertPos === dragTo
}

export function isInsertInsideDraggedBlock(insertPos: number, dragFrom: number, dragTo: number): boolean {
  return insertPos > dragFrom && insertPos < dragTo
}

export function eventTargetElement(target: EventTarget | null): Element | null {
  if (target == null || typeof Element === 'undefined') return null
  if (target instanceof Element) return target
  if (typeof Text !== 'undefined' && target instanceof Text) return target.parentElement
  return null
}

export function isBlockReorderExemptTarget(target: EventTarget | null): boolean {
  return Boolean(eventTargetElement(target)?.closest(BLOCK_REORDER_EXEMPT_SELECTOR))
}

export function isToggleSummaryTarget(target: EventTarget | null): boolean {
  return Boolean(
    eventTargetElement(target)?.closest(
      '.buildin-toggle-header, details.buildin-toggle > summary',
    ),
  )
}

export function isToggleHeaderReorderTarget(target: EventTarget | null): boolean {
  const el = eventTargetElement(target)
  if (!el) return false
  if (el.closest('.buildin-toggle-delete')) return false
  return isToggleSummaryTarget(el)
}

export function isToggleBodyReorderTarget(target: EventTarget | null): boolean {
  return Boolean(eventTargetElement(target)?.closest('.buildin-toggle-body'))
}

/**
 * Единый якорь ручки/жеста у toggle:
 * шапка → весь раздел; тело → строка внутри, как обычный абзац.
 */
export function preferToggleAncestorForPointerTarget(target: EventTarget | null): boolean {
  if (isToggleBodyReorderTarget(target)) return false
  return isToggleSummaryTarget(target)
}

export function isBlockReorderHandleTarget(target: EventTarget | null): boolean {
  return Boolean(eventTargetElement(target)?.closest(BLOCK_REORDER_HANDLE_SELECTOR))
}

export function isTableReorderTarget(target: EventTarget | null): boolean {
  return Boolean(eventTargetElement(target)?.closest('table'))
}

export function blockReorderDropLineRect(
  sourceIndex: number,
  overIndex: number,
  rel: readonly BlockRelRect[],
  thickness = BLOCK_REORDER_DROP_LINE_PX,
): { top: number; left: number; width: number; height: number } | null {
  if (rel.length === 0) return null
  if (overIndex === sourceIndex) return null
  if (overIndex < 0 || overIndex >= rel.length) return null
  const target = rel[overIndex]
  if (!target) return null
  const top = overIndex < sourceIndex ? target.top : target.top + target.height - thickness
  return { top, left: target.left, width: target.width, height: thickness }
}

export function blockReorderHandleRect(
  block: { top: number; left: number },
  size: { width: number; height: number },
  gutterLeft = Number.NEGATIVE_INFINITY,
): { left: number; top: number } {
  if (Number.isFinite(gutterLeft)) {
    return { left: gutterLeft, top: block.top }
  }
  return { left: block.left - size.width, top: block.top }
}

/** Рельс ручки: сразу слева от колонки текста, не от сдвинутого margin блока. */
export function blockReorderHandleRailLeft(textColumnLeft: number, handleWidth: number): number {
  return textColumnLeft - handleWidth
}

/** Зазор между блоком и ручкой, в котором hover ещё не снимаем. */
export const BLOCK_REORDER_HANDLE_APPROACH_SLACK_PX = 12

export function isPointInBlockReorderHandleApproach(
  clientX: number,
  clientY: number,
  handle: { left: number; top: number; width: number; height: number },
  editorLeft: number,
  slack = BLOCK_REORDER_HANDLE_APPROACH_SLACK_PX,
): boolean {
  const left = Math.min(handle.left, editorLeft) - slack
  const right = Math.max(handle.left + handle.width, editorLeft) + slack
  const top = handle.top - slack
  const bottom = handle.top + handle.height + slack
  return clientX >= left && clientX <= right && clientY >= top && clientY <= bottom
}

/** Ручка живёт вне блока: не прятать, пока курсор в коридоре к ней. */
export function shouldKeepBlockReorderHandleVisible(params: {
  overEditor: boolean
  overHandle: boolean
  handleVisible: boolean
  clientX: number
  clientY: number
  handleRect: { left: number; top: number; width: number; height: number } | null
  editorLeft: number
}): boolean {
  if (params.overEditor || params.overHandle) return true
  if (!params.handleVisible || !params.handleRect) return false
  return isPointInBlockReorderHandleApproach(
    params.clientX,
    params.clientY,
    params.handleRect,
    params.editorLeft,
  )
}

/** Левая полоса карточки toggle: posAtCoords там часто даёт соседний абзац. */
export function isPointInBlockReorderHandleLane(
  clientX: number,
  clientY: number,
  handle: { left: number; top: number; width: number; height: number },
  block: { left: number; top: number; height: number },
  editorLeft: number,
  slack = BLOCK_REORDER_HANDLE_APPROACH_SLACK_PX,
): boolean {
  const left = Math.min(handle.left, editorLeft) - slack
  const right = block.left + slack
  const top = block.top - slack
  const bottom = block.top + block.height + slack
  return clientX >= left && clientX <= right && clientY >= top && clientY <= bottom
}

/**
 * Не пересчитывать якорь ручки: у NodeView-блока (toggle) уход влево
 * даёт posAtCoords соседнего абзаца, у обычного текста — нет.
 */
export function shouldHoldBlockReorderHandleWithoutResync(params: {
  overHandle: boolean
  handleVisible: boolean
  isAtomicBlock: boolean
  clientX: number
  clientY: number
  handleRect: { left: number; top: number; width: number; height: number } | null
  blockRect: { left: number; top: number; height: number } | null
  editorLeft: number
}): boolean {
  if (params.overHandle) return true
  if (!params.isAtomicBlock) return false
  if (!params.handleVisible || !params.handleRect) return false
  if (
    isPointInBlockReorderHandleApproach(
      params.clientX,
      params.clientY,
      params.handleRect,
      params.editorLeft,
    )
  ) {
    return true
  }
  if (!params.blockRect) return false
  return isPointInBlockReorderHandleLane(
    params.clientX,
    params.clientY,
    params.handleRect,
    params.blockRect,
    params.editorLeft,
  )
}

export function isBuildinToggleChromeTarget(target: EventTarget | null): boolean {
  return Boolean(eventTargetElement(target)?.closest('.buildin-toggle'))
}

/** Ghost пункта списка без родителя теряет маркер в одном ряду с текстом. */
export function previewListWrapperTagName(parentTagName: string | null | undefined): 'UL' | 'OL' {
  return parentTagName === 'OL' ? 'OL' : 'UL'
}

/** Якорь ручки: <table> не .tableWrapper; любой пункт списка — <li>, не внутренний <p>. */
export function resolveBlockReorderHandleEl(blockEl: HTMLElement): HTMLElement {
  if (blockEl.tagName === 'TABLE') return blockEl
  const table = blockEl.querySelector('table')
  if (table instanceof HTMLElement) return table
  const listItem = blockEl.closest('li')
  if (listItem instanceof HTMLElement) return listItem
  return blockEl
}

/** Как канбан / дерево документов: соседи едут transform'ом, overlay долетает в слот. */
export const BLOCK_REORDER_LAYOUT_MS = 200

export const BLOCK_REORDER_DROP_MS = 220

export const BLOCK_REORDER_EASING = 'cubic-bezier(0.25, 1, 0.5, 1)'

export function siblingReorderShiftY(
  index: number,
  sourceIndex: number,
  overIndex: number,
  stride: number,
): number {
  if (index === sourceIndex) return 0
  if (sourceIndex < overIndex && index > sourceIndex && index <= overIndex) return -stride
  if (sourceIndex > overIndex && index < sourceIndex && index >= overIndex) return stride
  return 0
}

export function siblingOverIndexFromY(clientY: number, midpoints: number[]): number {
  if (midpoints.length === 0) return 0
  let best = 0
  let bestDist = Math.abs(clientY - midpoints[0]!)
  for (let i = 1; i < midpoints.length; i += 1) {
    const dist = Math.abs(clientY - midpoints[i]!)
    if (dist < bestDist) {
      bestDist = dist
      best = i
    }
  }
  return best
}

export function insertPosForSiblingMove(
  ranges: { from: number; size: number }[],
  sourceIndex: number,
  overIndex: number,
): number {
  const source = ranges[sourceIndex]
  if (!source) return 0
  if (overIndex === sourceIndex || overIndex < 0 || overIndex >= ranges.length) {
    return source.from
  }
  if (overIndex > sourceIndex) {
    const target = ranges[overIndex]!
    return target.from + target.size
  }
  return ranges[overIndex]!.from
}

export function insertPosForKeyboardMove(
  ranges: { from: number; size: number }[],
  sourceFrom: number,
  direction: 'up' | 'down',
): number | null {
  const sourceIndex = ranges.findIndex((range) => range.from === sourceFrom)
  if (sourceIndex < 0) return null
  const overIndex = direction === 'up' ? sourceIndex - 1 : sourceIndex + 1
  if (overIndex < 0 || overIndex >= ranges.length) return null
  return insertPosForSiblingMove(ranges, sourceIndex, overIndex)
}
