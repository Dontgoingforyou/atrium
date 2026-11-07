import type { Editor } from '@tiptap/core'
import { TextSelection } from '@tiptap/pm/state'

import contentStyles from '@/styles/modules/tasks/RichTextEditorContent.module.css'
import {
  findBuildinToggleDepth,
  isCaretInsideNode,
  shouldApplyNativeSelectionFromPm,
  shouldFollowPmCaretAfterKey,
  shouldInterceptToggleBodyEnter,
  shouldSyncPmSelectionFromNative,
  shouldSyncToggleSelectionOnKey,
} from '@/domain/documents/buildinToggleSelection'

function mapNativeRangeToPmPos(
  posAtDOM: (node: Node, offset: number) => number,
  range: { startContainer: Node; startOffset: number },
): number | null {
  try {
    return posAtDOM(range.startContainer, range.startOffset)
  } catch {
    return null
  }
}

function clampDocPos(pos: number, size: number): number {
  return Math.max(0, Math.min(pos, size))
}

export function isNativeCaretInToggleBody(root: HTMLElement): boolean {
  const sel = window.getSelection()
  if (!sel?.anchorNode) return false
  const el = sel.anchorNode instanceof Element ? sel.anchorNode : sel.anchorNode.parentElement
  return Boolean(el?.closest('.buildin-toggle-body') && root.contains(el))
}

function trySplitListItem(editor: Editor, name: string): boolean {
  if (!editor.schema.nodes[name]) return false
  return editor.commands.splitListItem(name)
}

export function splitToggleBodyOnEnter(editor: Editor): boolean {
  if (findBuildinToggleDepth(editor.state.selection.$from) == null) return false
  if (trySplitListItem(editor, 'taskItem')) return true
  if (trySplitListItem(editor, 'listItem')) return true
  return editor.commands.splitBlock()
}

export function syncBuildinTogglePmSelectionFromNative(
  editor: Editor,
  contentDOM: HTMLElement,
  getPos: () => number | undefined,
): boolean {
  if (!editor.isEditable || editor.view.composing) return false
  const sel = window.getSelection()
  if (!sel || sel.rangeCount === 0) return false
  const range = sel.getRangeAt(0)
  const nativeInside =
    contentDOM.contains(range.startContainer) && contentDOM.contains(range.endContainer)
  const posAtDOM = (node: Node, offset: number) => editor.view.posAtDOM(node, offset)
  const mappedFrom = nativeInside
    ? mapNativeRangeToPmPos(posAtDOM, {
        startContainer: range.startContainer,
        startOffset: range.startOffset,
      })
    : null
  const mappedTo = nativeInside
    ? mapNativeRangeToPmPos(posAtDOM, {
        startContainer: range.endContainer,
        startOffset: range.endOffset,
      })
    : null
  const togglePos = getPos()
  const current = typeof togglePos === 'number' ? editor.state.doc.nodeAt(togglePos) : null
  if (
    !shouldSyncPmSelectionFromNative({
      nativeInsideContentDom: nativeInside,
      mappedFrom,
      mappedTo,
      togglePos: typeof togglePos === 'number' ? togglePos : null,
      toggleSize: current?.nodeSize ?? 0,
      pmFrom: editor.state.selection.from,
      pmTo: editor.state.selection.to,
    })
  ) {
    return false
  }
  if (mappedFrom == null || mappedTo == null) return false
  return editor.commands.command(({ tr, dispatch }) => {
    const from = clampDocPos(mappedFrom, tr.doc.content.size)
    const to = clampDocPos(mappedTo, tr.doc.content.size)
    tr.setSelection(TextSelection.create(tr.doc, Math.min(from, to), Math.max(from, to)))
    tr.setMeta('addToHistory', false)
    dispatch?.(tr)
    return true
  })
}

export function applyBuildinToggleNativeSelectionFromPm(
  editor: Editor,
  contentDOM: HTMLElement,
  getPos: () => number | undefined,
): boolean {
  const togglePos = getPos()
  const current = typeof togglePos === 'number' ? editor.state.doc.nodeAt(togglePos) : null
  if (typeof togglePos !== 'number' || !current || current.type.name !== 'buildinToggle') {
    return false
  }
  const pmFrom = editor.state.selection.from
  if (!isCaretInsideNode(pmFrom, togglePos, current.nodeSize)) return false

  const sel = window.getSelection()
  const nativeRange = sel && sel.rangeCount > 0 ? sel.getRangeAt(0) : null
  const nativeMappedPos =
    nativeRange && contentDOM.contains(nativeRange.startContainer)
      ? mapNativeRangeToPmPos((node, offset) => editor.view.posAtDOM(node, offset), nativeRange)
      : null
  if (
    !shouldApplyNativeSelectionFromPm({
      pmInsideToggle: true,
      nativeMappedPos,
      pmFrom,
    })
  ) {
    return false
  }

  let found: { node: Node; offset: number }
  try {
    found = editor.view.domAtPos(pmFrom)
  } catch {
    return false
  }
  if (found.node !== contentDOM && !contentDOM.contains(found.node)) return false
  if (!sel) return false
  try {
    const next = document.createRange()
    next.setStart(found.node, found.offset)
    next.collapse(true)
    sel.removeAllRanges()
    sel.addRange(next)
    return true
  } catch {
    return false
  }
}

export function bindBuildinToggleBodyCaret(
  editor: Editor,
  contentDOM: HTMLElement,
  getPos: () => number | undefined,
  onChromeSync: () => void,
): { destroy: () => void } {
  let followPmAfterEnter = false
  const syncFromNative = () => {
    if (editor.view.dom.classList.contains(contentStyles.isBlockReordering)) return
    syncBuildinTogglePmSelectionFromNative(editor, contentDOM, getPos)
  }
  const onEditorUpdate = () => {
    onChromeSync()
    if (!followPmAfterEnter) return
    followPmAfterEnter = false
    applyBuildinToggleNativeSelectionFromPm(editor, contentDOM, getPos)
  }
  const onBodyKeyDownCapture = (event: KeyboardEvent) => {
    if (shouldSyncToggleSelectionOnKey(event.key)) {
      syncFromNative()
    }
    if (!shouldFollowPmCaretAfterKey(event.key) || !shouldInterceptToggleBodyEnter(event)) {
      return
    }
    event.preventDefault()
    event.stopPropagation()
    event.stopImmediatePropagation()
    followPmAfterEnter = true
    splitToggleBodyOnEnter(editor)
  }
  contentDOM.addEventListener('keydown', onBodyKeyDownCapture, true)
  contentDOM.addEventListener('pointerup', syncFromNative)
  editor.on('update', onEditorUpdate)
  return {
    destroy() {
      editor.off('update', onEditorUpdate)
      contentDOM.removeEventListener('keydown', onBodyKeyDownCapture, true)
      contentDOM.removeEventListener('pointerup', syncFromNative)
    },
  }
}
