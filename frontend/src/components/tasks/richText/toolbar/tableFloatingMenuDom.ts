import type { Node as ProseMirrorNode } from '@tiptap/pm/model'
import type { Editor } from '@tiptap/react'

import {
  BLOCK_REORDER_HANDLE_SELECTOR,
  eventTargetElement,
  isBlockReorderHandleTarget,
} from '@/domain/documents/richTextBlockReorder'

export const TABLE_FLOAT_SLOT_ATTR = 'data-table-float-slot'

export const TABLE_FLOAT_MENU_SELECTOR = '[data-table-float-menu]'

const HANDLE_TABLE_PROBE_PX = 8

export function findTableWrapperFromTarget(target: EventTarget | null): HTMLElement | null {
  const el = eventTargetElement(target)?.closest('.tableWrapper')
  return el instanceof HTMLElement ? el : null
}

export function findActiveTableWrapper(editor: Editor): HTMLElement | null {
  const { view, state } = editor
  try {
    const domAt = view.domAtPos(state.selection.from)
    const el = domAt.node instanceof Element ? domAt.node : domAt.node.parentElement
    return findTableWrapperFromTarget(el)
  } catch {
    return null
  }
}

export function findTableWrapperAtPoint(editor: Editor, clientX: number, clientY: number): HTMLElement | null {
  if (typeof document !== 'undefined') {
    const hit = document.elementFromPoint(clientX, clientY)
    const fromHit = findTableWrapperFromTarget(hit)
    if (fromHit && editor.view.dom.contains(fromHit)) return fromHit
  }
  try {
    const coords = editor.view.posAtCoords({ left: clientX, top: clientY })
    if (!coords) return null
    const domAt = editor.view.domAtPos(coords.pos)
    const el = domAt.node instanceof Element ? domAt.node : domAt.node.parentElement
    return findTableWrapperFromTarget(el)
  } catch {
    return null
  }
}

export function findTableWrapperNearHandle(editor: Editor, handleEl: Element): HTMLElement | null {
  const rect = handleEl.getBoundingClientRect()
  return findTableWrapperAtPoint(editor, rect.right + HANDLE_TABLE_PROBE_PX, rect.top + rect.height / 2)
}

export function isTableFloatMenuTarget(target: EventTarget | null): boolean {
  return Boolean(eventTargetElement(target)?.closest(TABLE_FLOAT_MENU_SELECTOR))
}

export function resolveTableFloatWrapper(editor: Editor, event: MouseEvent | null): HTMLElement | null {
  if (!editor.isEditable) return null
  if (event) {
    const hovered = findTableWrapperFromTarget(event.target)
    if (hovered) return hovered
    if (isBlockReorderHandleTarget(event.target)) {
      const handle = eventTargetElement(event.target)?.closest(BLOCK_REORDER_HANDLE_SELECTOR)
      if (handle) {
        const near = findTableWrapperNearHandle(editor, handle)
        if (near) return near
      }
    }
    if (isTableFloatMenuTarget(event.target)) return null
  }
  if (editor.isActive('table')) return findActiveTableWrapper(editor)
  return null
}

function tableAtDom(editor: Editor, tableEl: HTMLElement): { node: ProseMirrorNode; start: number } | null {
  const pos = editor.view.posAtDOM(tableEl, 0)
  const $pos = editor.state.doc.resolve(pos)
  for (let depth = $pos.depth; depth > 0; depth -= 1) {
    if ($pos.node(depth).type.name === 'table') {
      return { node: $pos.node(depth), start: $pos.start(depth) }
    }
  }
  if ($pos.nodeAfter?.type.name === 'table') {
    return { node: $pos.nodeAfter, start: $pos.pos + 1 }
  }
  return null
}

function caretInLastCell(tableNode: ProseMirrorNode, tableStart: number): number | null {
  const lastRow = tableNode.lastChild
  if (!lastRow || lastRow.childCount === 0) return null
  let pos = tableStart
  for (let index = 0; index < tableNode.childCount - 1; index += 1) {
    pos += tableNode.child(index).nodeSize
  }
  pos += 1
  for (let index = 0; index < lastRow.childCount - 1; index += 1) {
    pos += lastRow.child(index).nodeSize
  }
  pos += 1
  if (lastRow.lastChild?.firstChild?.isTextblock) pos += 1
  return pos
}

export function selectIntoTableWrapper(editor: Editor, wrapper: HTMLElement): boolean {
  if (findActiveTableWrapper(editor) === wrapper) return true
  const table = wrapper.querySelector(':scope > table')
  if (!(table instanceof HTMLElement)) return false
  try {
    const found = tableAtDom(editor, table)
    if (!found) return false
    const caret = caretInLastCell(found.node, found.start)
    if (caret == null) return false
    return editor.chain().focus().setTextSelection(caret).run()
  } catch {
    return false
  }
}

export function findOrCreateTableFloatSlot(wrapper: HTMLElement, slotClassName: string): HTMLElement {
  let slot = Array.from(wrapper.children).find(
    (child): child is HTMLElement => child instanceof HTMLElement && child.hasAttribute(TABLE_FLOAT_SLOT_ATTR),
  )
  if (!slot) {
    slot = document.createElement('div')
    slot.setAttribute(TABLE_FLOAT_SLOT_ATTR, '')
    slot.className = slotClassName
    wrapper.appendChild(slot)
  }
  return slot
}
