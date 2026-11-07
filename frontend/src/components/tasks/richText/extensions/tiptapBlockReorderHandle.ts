import contentStyles from '@/styles/modules/tasks/RichTextEditorContent.module.css'
import {
  BLOCK_REORDER_HANDLE_ATTR,
  blockReorderHandleRailLeft,
  blockReorderHandleRect,
  resolveBlockReorderHandleEl,
  isBlockReorderHandleTarget,
  shouldHoldBlockReorderHandleWithoutResync,
  shouldKeepBlockReorderHandleVisible,
  shouldShowBlockReorderHandle,
  type BlockReorderHandleVisibility,
} from '@/domain/documents/richTextBlockReorder'

const HANDLE_LABEL = 'Переместить блок'
const HANDLE_FALLBACK_SIZE = { width: 24, height: 24 }

export type BlockReorderHandleRange = { from: number; size: number }

export type BlockReorderHandle = {
  el: HTMLElement
  range: BlockReorderHandleRange | null
}

type RangeFromPointer = (
  pos: number,
  target: EventTarget | null,
) => BlockReorderHandleRange | null

export function createBlockReorderHandle(layer: HTMLElement = document.body): BlockReorderHandle {
  const el = document.createElement('div')
  el.className = contentStyles.blockDragHandle
  el.setAttribute(BLOCK_REORDER_HANDLE_ATTR, '')
  el.setAttribute('role', 'button')
  el.setAttribute('aria-label', HANDLE_LABEL)
  el.title = HANDLE_LABEL
  el.textContent = '⋮⋮'
  el.hidden = true
  layer.appendChild(el)
  return { el, range: null }
}

export function moveBlockReorderHandle(
  handle: BlockReorderHandle,
  blockEl: HTMLElement,
  range: BlockReorderHandleRange,
  gutterLeft = Number.NEGATIVE_INFINITY,
): void {
  handle.el.hidden = false
  const measuredWidth = handle.el.offsetWidth
  const measuredHeight = handle.el.offsetHeight
  const size = {
    width: measuredWidth || HANDLE_FALLBACK_SIZE.width,
    height: measuredHeight || HANDLE_FALLBACK_SIZE.height,
  }
  const rect = resolveBlockReorderHandleEl(blockEl).getBoundingClientRect()
  const railLeft = Number.isFinite(gutterLeft)
    ? blockReorderHandleRailLeft(gutterLeft, size.width)
    : Number.NEGATIVE_INFINITY
  const pos = blockReorderHandleRect({ top: rect.top, left: rect.left }, size, railLeft)
  handle.el.style.left = `${pos.left}px`
  handle.el.style.top = `${pos.top}px`
  handle.range = range
}

export function hideBlockReorderHandle(handle: BlockReorderHandle): void {
  handle.el.hidden = true
  handle.range = null
}

export function destroyBlockReorderHandle(handle: BlockReorderHandle): void {
  hideBlockReorderHandle(handle)
  handle.el.remove()
}

export function syncBlockReorderHandle(
  handle: BlockReorderHandle,
  event: MouseEvent,
  opts: {
    editable: boolean
    busy: boolean
    posAtCoords: (clientX: number, clientY: number) => number | null
    nodeDom: (from: number) => HTMLElement | null
    rangeFromPointer: RangeFromPointer
    visibility: (from: number) => BlockReorderHandleVisibility
    gutterLeft: () => number
  },
): void {
  if (!opts.editable || opts.busy) {
    hideBlockReorderHandle(handle)
    return
  }
  if (isBlockReorderHandleTarget(event.target)) return
  const editorLeft = opts.gutterLeft()
  const handleRect = handle.el.hidden ? null : handle.el.getBoundingClientRect()
  const currentBlock = handle.range && !handle.el.hidden ? opts.nodeDom(handle.range.from) : null
  const blockRect = currentBlock ? currentBlock.getBoundingClientRect() : null
  if (
    shouldHoldBlockReorderHandleWithoutResync({
      overHandle: false,
      handleVisible: !handle.el.hidden,
      isAtomicBlock: Boolean(handle.range && opts.visibility(handle.range.from).isAtomicBlock),
      clientX: event.clientX,
      clientY: event.clientY,
      handleRect,
      blockRect,
      editorLeft,
    })
  ) {
    return
  }
  const pos = opts.posAtCoords(event.clientX, event.clientY)
  if (pos == null) {
    if (
      shouldKeepBlockReorderHandleVisible({
        overEditor: false,
        overHandle: false,
        handleVisible: !handle.el.hidden,
        clientX: event.clientX,
        clientY: event.clientY,
        handleRect,
        editorLeft,
      })
    ) {
      return
    }
    hideBlockReorderHandle(handle)
    return
  }
  const range = opts.rangeFromPointer(pos, event.target)
  if (!range) {
    hideBlockReorderHandle(handle)
    return
  }
  if (!shouldShowBlockReorderHandle(opts.visibility(range.from))) {
    hideBlockReorderHandle(handle)
    return
  }
  const blockEl = opts.nodeDom(range.from)
  if (!blockEl) {
    hideBlockReorderHandle(handle)
    return
  }
  moveBlockReorderHandle(handle, blockEl, range, opts.gutterLeft())
}
