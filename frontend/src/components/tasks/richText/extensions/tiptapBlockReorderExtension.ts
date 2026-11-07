import { Extension } from '@tiptap/core'
import type { Node as PmNode } from '@tiptap/pm/model'
import { Plugin, PluginKey, type EditorState, type Transaction } from '@tiptap/pm/state'
import type { EditorView } from '@tiptap/pm/view'

import contentStyles from '@/styles/modules/tasks/RichTextEditorContent.module.css'
import {
  eventTargetElement,
  insertPosForKeyboardMove,
  insertPosForSiblingMove,
  isAtomicReorderBlock,
  isBlockReorderExemptTarget,
  isBlockReorderHandleTarget,
  isInsertInsideDraggedBlock,
  isSameBlockDrop,
  isToggleHeaderReorderTarget,
  preferToggleAncestorForPointerTarget,
  mappedInsertPosAfterDelete,
  canBeginBlockReorderGesture,
  resolveBlockReorderGestureOrigin,
  type BlockReorderGestureOrigin,
  shouldHoldBlockReorderHandleWithoutResync,
  shouldKeepBlockReorderHandleVisible,
  shouldShowBlockReorderHandle,
  shouldStartBlockReorder,
  shouldSuppressClickAfterBlockReorder,
  type BlockReorderHandleVisibility,
} from '@/domain/documents/richTextBlockReorder'

import {
  createBlockReorderHandle,
  destroyBlockReorderHandle,
  hideBlockReorderHandle,
  syncBlockReorderHandle,
  type BlockReorderHandle,
} from './tiptapBlockReorderHandle'
import {
  destroyBlockReorderPreview,
  freezeBlockReorderPreview,
  moveBlockReorderPreview,
  settleBlockReorderPreview,
  startBlockReorderPreview,
  type BlockReorderPreview,
} from './tiptapBlockReorderPreview'

const pluginKey = new PluginKey('blockReorder')

type DragState = {
  from: number
  size: number
  startX: number
  startY: number
  active: boolean
  origin: BlockReorderGestureOrigin
  preview: BlockReorderPreview | null
  ranges: { from: number; size: number }[] | null
}

declare module '@tiptap/core' {
  interface Commands<ReturnType> {
    blockReorder: {
      moveRichTextBlock: (direction: 'up' | 'down', blockFrom?: number) => ReturnType
    }
  }
}

export function findNamedAncestorBlockRange(
  doc: PmNode,
  pos: number,
  typeName: string,
): { from: number; size: number } | null {
  if (pos < 0) return null
  const $pos = doc.resolve(Math.min(pos, doc.content.size))
  for (let depth = $pos.depth; depth > 0; depth -= 1) {
    if ($pos.node(depth).type.name !== typeName) continue
    return { from: $pos.before(depth), size: $pos.node(depth).nodeSize }
  }
  if ($pos.nodeAfter?.type.name === typeName) {
    return { from: $pos.pos, size: $pos.nodeAfter.nodeSize }
  }
  if ($pos.nodeBefore?.type.name === typeName) {
    const node = $pos.nodeBefore
    return { from: $pos.pos - node.nodeSize, size: node.nodeSize }
  }
  return null
}

export function findToggleAncestorBlockRange(doc: PmNode, pos: number): { from: number; size: number } | null {
  return findNamedAncestorBlockRange(doc, pos, 'buildinToggle')
}

export function findTableAncestorBlockRange(doc: PmNode, pos: number): { from: number; size: number } | null {
  return findNamedAncestorBlockRange(doc, pos, 'table')
}

function nearestChildBlockRange(
  doc: PmNode,
  parentFrom: number,
  pos: number,
): { from: number; size: number } | null {
  const parent = doc.nodeAt(parentFrom)
  if (!parent || parent.childCount === 0) return null
  let childFrom = parentFrom + 1
  let best: { from: number; size: number } | null = null
  let bestDist = Infinity
  parent.forEach((child) => {
    if (child.isBlock) {
      const childTo = childFrom + child.nodeSize
      const dist = pos < childFrom ? childFrom - pos : pos >= childTo ? pos - childTo : 0
      if (dist < bestDist) {
        bestDist = dist
        best = { from: childFrom, size: child.nodeSize }
      }
    }
    childFrom += child.nodeSize
  })
  return best
}

const LIST_ITEM_TYPE_NAMES = ['taskItem', 'listItem'] as const
const LIST_TYPE_NAMES = ['taskList', 'bulletList', 'orderedList'] as const

function isListTypeName(name: string): boolean {
  return (LIST_TYPE_NAMES as readonly string[]).includes(name)
}

/** Один пункт — едет весь список, иначе строка остаётся в ul и не меняется местами с абзацами. */
function liftSingletonListRange(
  doc: PmNode,
  item: { from: number; size: number },
): { from: number; size: number } {
  const $pos = doc.resolve(item.from)
  const parent = $pos.parent
  if (parent.childCount !== 1 || !isListTypeName(parent.type.name)) return item
  return { from: $pos.before($pos.depth), size: parent.nodeSize }
}

function findListItemMovableRange(doc: PmNode, pos: number): { from: number; size: number } | null {
  for (const typeName of LIST_ITEM_TYPE_NAMES) {
    const item = findNamedAncestorBlockRange(doc, pos, typeName)
    if (item) return liftSingletonListRange(doc, item)
  }
  for (const typeName of LIST_TYPE_NAMES) {
    const list = findNamedAncestorBlockRange(doc, pos, typeName)
    if (!list) continue
    const child = nearestChildBlockRange(doc, list.from, pos)
    if (!child) return list
    return liftSingletonListRange(doc, child)
  }
  return null
}

export function findMovableBlockRange(doc: PmNode, pos: number): { from: number; size: number } | null {
  const listItem = findListItemMovableRange(doc, pos)
  if (listItem) return listItem
  if (pos < 0) return null
  const $pos = doc.resolve(Math.min(pos, doc.content.size))
  if ($pos.parent.isTextblock && $pos.depth >= 1) {
    return { from: $pos.before($pos.depth), size: $pos.parent.nodeSize }
  }
  if ($pos.nodeAfter?.isBlock) {
    return { from: $pos.pos, size: $pos.nodeAfter.nodeSize }
  }
  if ($pos.nodeBefore?.isBlock) {
    const node = $pos.nodeBefore
    return { from: $pos.pos - node.nodeSize, size: node.nodeSize }
  }
  if ($pos.depth >= 1) {
    return { from: $pos.before($pos.depth), size: $pos.node($pos.depth).nodeSize }
  }
  return null
}

function rangeFromPointer(doc: PmNode, pos: number, target: EventTarget | null): { from: number; size: number } | null {
  const tableRange = findTableAncestorBlockRange(doc, pos)
  if (tableRange) return tableRange
  if (preferToggleAncestorForPointerTarget(target)) {
    return findToggleAncestorBlockRange(doc, pos) ?? findMovableBlockRange(doc, pos)
  }
  return findMovableBlockRange(doc, pos)
}

function rangeFromToggleHeaderDom(
  view: EditorView,
  target: EventTarget | null,
): { from: number; size: number } | null {
  const root = eventTargetElement(target)?.closest('.buildin-toggle')
  if (!(root instanceof HTMLElement)) return null
  try {
    const pos = view.posAtDOM(root, 0)
    return findToggleAncestorBlockRange(view.state.doc, pos) ?? findMovableBlockRange(view.state.doc, pos)
  } catch {
    return null
  }
}

function visibilityForBlock(doc: PmNode, from: number): BlockReorderHandleVisibility {
  const node = doc.nodeAt(from)
  if (!node) return { textLength: 0, isAtomicBlock: false }
  return {
    textLength: node.textContent.trim().length,
    isAtomicBlock: isAtomicReorderBlock(node.type.name),
  }
}

export function collectSiblingBlockRanges(doc: PmNode, from: number): { from: number; size: number }[] | null {
  if (from < 0 || from > doc.content.size) return null
  const $pos = doc.resolve(from)
  if (!$pos.nodeAfter?.isBlock) return null
  const ranges: { from: number; size: number }[] = []
  let pos = $pos.start()
  $pos.parent.forEach((child) => {
    ranges.push({ from: pos, size: child.nodeSize })
    pos += child.nodeSize
  })
  return ranges
}

export function isDropInSameReorderGroup(doc: PmNode, dragFrom: number, dropFrom: number): boolean {
  if (dragFrom < 0 || dropFrom < 0) return false
  const safeDrag = Math.min(dragFrom, doc.content.size)
  const safeDrop = Math.min(dropFrom, doc.content.size)
  if (doc.resolve(safeDrag).start() === doc.resolve(safeDrop).start()) return true
  const dropNode = doc.nodeAt(safeDrop)
  if (!dropNode) return false
  return safeDrag > safeDrop && safeDrag < safeDrop + dropNode.nodeSize
}

/** Слот среди соседей только в той же группе; иначе пункт можно вынести, обернув в список. */
export function shouldUseSiblingBlockReorder(
  doc: PmNode,
  dragFrom: number,
  dropFrom: number,
): boolean {
  return isDropInSameReorderGroup(doc, dragFrom, dropFrom)
}

export function buildBlockReorderTransaction(
  state: EditorState,
  dragFrom: number,
  dragSize: number,
  insertPos: number,
): Transaction | null {
  const dragTo = dragFrom + dragSize
  if (isSameBlockDrop(insertPos, dragFrom, dragTo)) return null
  if (isInsertInsideDraggedBlock(insertPos, dragFrom, dragTo)) return null
  const node = state.doc.nodeAt(dragFrom)
  if (!node) return null
  const wrapperType = state.doc.resolve(dragFrom).parent.type
  const mapped = mappedInsertPosAfterDelete(insertPos, dragFrom, dragSize)
  const tr = state.tr.delete(dragFrom, dragFrom + dragSize)
  const $ins = tr.doc.resolve(mapped)
  if ($ins.parent.canReplaceWith($ins.index(), $ins.index(), node.type)) {
    return tr.insert(mapped, node)
  }
  if (node.type.name !== 'taskItem' && node.type.name !== 'listItem') return null
  const wrapped = wrapperType.create(null, node)
  if (!$ins.parent.canReplaceWith($ins.index(), $ins.index(), wrapped.type)) return null
  return tr.insert(mapped, wrapped)
}

export function applyBlockReorder(
  view: EditorView,
  dragFrom: number,
  dragSize: number,
  insertPos: number,
): boolean {
  const tr = buildBlockReorderTransaction(view.state, dragFrom, dragSize, insertPos)
  if (!tr) return false
  view.dispatch(tr.scrollIntoView())
  return true
}

function dropPlace(
  view: EditorView,
  clientX: number,
  clientY: number,
  target: EventTarget | null,
): { insertPos: number; from: number } | null {
  const coords = view.posAtCoords({ left: clientX, top: clientY })
  if (!coords) return { insertPos: view.state.doc.content.size, from: view.state.doc.content.size }
  const range = rangeFromPointer(view.state.doc, coords.pos, target)
  if (!range) return { insertPos: view.state.doc.content.size, from: view.state.doc.content.size }
  const dom = view.nodeDOM(range.from)
  if (!(dom instanceof HTMLElement)) return { insertPos: range.from, from: range.from }
  const rect = dom.getBoundingClientRect()
  const insertPos = clientY < rect.top + rect.height / 2 ? range.from : range.from + range.size
  return { insertPos, from: range.from }
}

function siblingDomEls(
  view: EditorView,
  ranges: { from: number; size: number }[],
): HTMLElement[] | null {
  const els: HTMLElement[] = []
  for (const range of ranges) {
    const el = view.nodeDOM(range.from)
    if (!(el instanceof HTMLElement)) return null
    els.push(el)
  }
  return els
}

function resolveInsertPos(
  view: EditorView,
  event: MouseEvent,
  drag: DragState,
): number | null {
  const drop = dropPlace(view, event.clientX, event.clientY, event.target)
  if (!drop) return null
  const preview = drag.preview
  const ranges = drag.ranges
  if (
    preview &&
    ranges &&
    shouldUseSiblingBlockReorder(view.state.doc, drag.from, drop.from)
  ) {
    return insertPosForSiblingMove(ranges, preview.sourceIndex, preview.overIndex)
  }
  return drop.insertPos
}

function rangeForKeyboardMove(doc: PmNode, selectionPos: number, blockFrom?: number): { from: number; size: number } | null {
  if (blockFrom != null) {
    const node = doc.nodeAt(blockFrom)
    if (node?.isBlock) return { from: blockFrom, size: node.nodeSize }
  }
  return findMovableBlockRange(doc, selectionPos)
}

function createBlockReorderPlugin(): Plugin {
  return new Plugin({
    key: pluginKey,
    view(view) {
      let drag: DragState | null = null
      let settling = false
      let closed = false
      let livePreview: BlockReorderPreview | null = null
      const handle: BlockReorderHandle | null =
        typeof document !== 'undefined' ? createBlockReorderHandle(document.body) : null

      const activatePreview = (current: DragState) => {
        const ranges = collectSiblingBlockRanges(view.state.doc, current.from)
        const sourceEl = view.nodeDOM(current.from)
        if (!(sourceEl instanceof HTMLElement) || !ranges) return
        const sourceIndex = ranges.findIndex((range) => range.from === current.from)
        const siblingEls = siblingDomEls(view, ranges)
        if (sourceIndex < 0 || !siblingEls) return
        current.ranges = ranges
        current.preview = startBlockReorderPreview(
          sourceEl,
          siblingEls,
          sourceIndex,
          current.startX,
          current.startY,
        )
        livePreview = current.preview
      }

      const onMove = (event: MouseEvent) => {
        if (!drag) return
        if (!drag.active) {
          const dx = event.clientX - drag.startX
          const dy = event.clientY - drag.startY
          if (!shouldStartBlockReorder(dx, dy, { origin: drag.origin })) return
          drag.active = true
          if (handle) hideBlockReorderHandle(handle)
          view.dom.classList.add(contentStyles.isBlockReordering)
          window.getSelection()?.removeAllRanges()
          activatePreview(drag)
        }
        event.preventDefault()
        if (!drag.preview) return
        const drop = dropPlace(view, event.clientX, event.clientY, event.target)
        const sameParent = Boolean(
          drop &&
            shouldUseSiblingBlockReorder(
              view.state.doc,
              drag.from,
              drop.from,
            ),
        )
        moveBlockReorderPreview(drag.preview, event.clientX, event.clientY, sameParent)
      }

      const finishDrag = (event: MouseEvent, current: DragState) => {
        const insertPos = resolveInsertPos(view, event, current)
        const commit = () => {
          if (closed) return
          if (current.preview) freezeBlockReorderPreview(current.preview)
          if (insertPos != null) {
            applyBlockReorder(view, current.from, current.size, insertPos)
          }
          if (current.preview) destroyBlockReorderPreview(current.preview)
          livePreview = null
          view.dom.classList.remove(contentStyles.isBlockReordering)
          settling = false
        }
        if (!current.preview) {
          commit()
          return
        }
        settling = true
        settleBlockReorderPreview(current.preview, commit)
      }

      const onUp = (event: MouseEvent) => {
        window.removeEventListener('mousemove', onMove, true)
        window.removeEventListener('mouseup', onUp, true)
        const current = drag
        drag = null
        if (!current?.active) {
          view.dom.classList.remove(contentStyles.isBlockReordering)
          return
        }
        if (shouldSuppressClickAfterBlockReorder(true)) {
          const suppressClick = (clickEvent: Event) => {
            clickEvent.preventDefault()
            clickEvent.stopPropagation()
          }
          view.dom.addEventListener('click', suppressClick, { capture: true, once: true })
        }
        finishDrag(event, current)
      }

      const onHoverMove = (event: MouseEvent) => {
        if (!handle) return
        const overEditor = view.dom.contains(event.target as Node)
        const overHandle = handle.el.contains(event.target as Node)
        const editorLeft = view.dom.getBoundingClientRect().left
        const handleRect = handle.el.hidden ? null : handle.el.getBoundingClientRect()
        const currentBlock =
          handle.range && !handle.el.hidden ? view.nodeDOM(handle.range.from) : null
        const blockRect = currentBlock instanceof HTMLElement ? currentBlock.getBoundingClientRect() : null
        const keepVisible = shouldKeepBlockReorderHandleVisible({
          overEditor,
          overHandle,
          handleVisible: !handle.el.hidden,
          clientX: event.clientX,
          clientY: event.clientY,
          handleRect,
          editorLeft,
        })
        if (!keepVisible) {
          if (!drag) hideBlockReorderHandle(handle)
          return
        }
        const holdAnchor = shouldHoldBlockReorderHandleWithoutResync({
          overHandle,
          handleVisible: !handle.el.hidden,
          isAtomicBlock: Boolean(
            handle.range && visibilityForBlock(view.state.doc, handle.range.from).isAtomicBlock,
          ),
          clientX: event.clientX,
          clientY: event.clientY,
          handleRect,
          blockRect,
          editorLeft,
        })
        if (holdAnchor || (!overEditor && !overHandle)) return
        syncBlockReorderHandle(handle, event, {
          editable: view.editable,
          busy: Boolean(drag?.active || settling),
          posAtCoords: (clientX, clientY) => {
            const coords = view.posAtCoords({ left: clientX, top: clientY })
            return coords?.pos ?? null
          },
          nodeDom: (from) => {
            const el = view.nodeDOM(from)
            return el instanceof HTMLElement ? el : null
          },
          rangeFromPointer: (pos, target) => {
            if (preferToggleAncestorForPointerTarget(target)) {
              return rangeFromToggleHeaderDom(view, target) ?? rangeFromPointer(view.state.doc, pos, target)
            }
            return rangeFromPointer(view.state.doc, pos, target)
          },
          visibility: (from) => visibilityForBlock(view.state.doc, from),
          gutterLeft: () => view.dom.getBoundingClientRect().left,
        })
      }

      const onDown = (event: MouseEvent) => {
        if (settling) return
        if (event.button !== 0 || event.ctrlKey || event.metaKey) return
        if (!view.editable) return
        const fromHandle = isBlockReorderHandleTarget(event.target)
        const fromToggleHeader = isToggleHeaderReorderTarget(event.target)
        if (!fromHandle && !fromToggleHeader && isBlockReorderExemptTarget(event.target)) return
        const origin = resolveBlockReorderGestureOrigin(fromHandle, fromToggleHeader)
        if (!canBeginBlockReorderGesture(origin)) return
        let range = fromHandle ? handle?.range ?? null : null
        if (!range) {
          const coords = view.posAtCoords({ left: event.clientX, top: event.clientY })
          if (coords) {
            range = rangeFromPointer(view.state.doc, coords.pos, event.target)
          }
        }
        if (!range && fromToggleHeader) {
          range = rangeFromToggleHeaderDom(view, event.target)
        }
        if (!range) return
        if (!shouldShowBlockReorderHandle(visibilityForBlock(view.state.doc, range.from))) return
        drag = {
          from: range.from,
          size: range.size,
          startX: event.clientX,
          startY: event.clientY,
          active: fromHandle,
          origin,
          preview: null,
          ranges: null,
        }
        if (fromHandle) {
          event.preventDefault()
          if (handle) hideBlockReorderHandle(handle)
          view.dom.classList.add(contentStyles.isBlockReordering)
          window.getSelection()?.removeAllRanges()
          activatePreview(drag)
        }
        window.addEventListener('mousemove', onMove, true)
        window.addEventListener('mouseup', onUp, true)
      }

      view.dom.addEventListener('mousedown', onDown, true)
      handle?.el.addEventListener('mousedown', onDown, true)
      window.addEventListener('mousemove', onHoverMove, true)
      return {
        destroy() {
          closed = true
          view.dom.removeEventListener('mousedown', onDown, true)
          handle?.el.removeEventListener('mousedown', onDown, true)
          window.removeEventListener('mousemove', onHoverMove, true)
          window.removeEventListener('mousemove', onMove, true)
          window.removeEventListener('mouseup', onUp, true)
          if (livePreview) destroyBlockReorderPreview(livePreview)
          if (handle) destroyBlockReorderHandle(handle)
          livePreview = null
          drag = null
          view.dom.classList.remove(contentStyles.isBlockReordering)
        },
      }
    },
  })
}

export const BlockReorder = Extension.create({
  name: 'blockReorder',
  addCommands() {
    return {
      moveRichTextBlock:
        (direction, blockFrom) =>
        ({ editor, state, dispatch }) => {
          if (!editor.isEditable) return false
          const range = rangeForKeyboardMove(state.doc, state.selection.from, blockFrom)
          if (!range) return false
          const ranges = collectSiblingBlockRanges(state.doc, range.from)
          if (!ranges) return false
          const insertPos = insertPosForKeyboardMove(ranges, range.from, direction)
          if (insertPos == null) return false
          const tr = buildBlockReorderTransaction(state, range.from, range.size, insertPos)
          if (!tr) return false
          dispatch?.(tr.scrollIntoView())
          return true
        },
    }
  },
  addKeyboardShortcuts() {
    return {
      'Alt-ArrowUp': () => this.editor.commands.moveRichTextBlock('up'),
      'Alt-ArrowDown': () => this.editor.commands.moveRichTextBlock('down'),
    }
  },
  addProseMirrorPlugins() {
    return [createBlockReorderPlugin()]
  },
})
