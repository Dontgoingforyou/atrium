import type { Editor } from '@tiptap/core'
import { TextSelection } from '@tiptap/pm/state'

import {
  emptyParagraphAfterToggleRange,
  resolveBuildinToggleBodyCaretPos,
} from '@/domain/documents/buildinToggleTitle'

function dropEmptyParagraphAfterToggleAndSelectBody(editor: Editor, togglePos: number): boolean {
  return editor.commands.command(({ tr, dispatch }) => {
    const node = tr.doc.nodeAt(togglePos)
    if (!node || node.type.name !== 'buildinToggle') return false
    const after = togglePos + node.nodeSize
    const next = after < tr.doc.content.size ? tr.doc.nodeAt(after) : null
    const extra = emptyParagraphAfterToggleRange({
      togglePos,
      toggleSize: node.nodeSize,
      nextTypeName: next?.type.name ?? null,
      nextNodeSize: next?.nodeSize ?? 0,
      nextEmpty: Boolean(next && next.content.size === 0),
    })
    if (extra) {
      tr.delete(extra.from, extra.to)
    }
    const inner = tr.doc.nodeAt(togglePos)
    if (!inner) return false
    const caret = resolveBuildinToggleBodyCaretPos(togglePos, inner.nodeSize)
    if (caret == null) return false
    tr.setSelection(TextSelection.create(tr.doc, caret))
    dispatch?.(tr)
    return true
  })
}

export function enterToggleBodyFromTitle(
  editor: Editor,
  togglePos: number,
  attrs: { title: string; open: boolean },
): void {
  editor.commands.command(({ tr }) => {
    const current = tr.doc.nodeAt(togglePos)
    if (!current || current.type.name !== 'buildinToggle') return false
    tr.setNodeMarkup(togglePos, undefined, { ...current.attrs, ...attrs })
    return true
  })
  dropEmptyParagraphAfterToggleAndSelectBody(editor, togglePos)
  editor.view.focus()
  dropEmptyParagraphAfterToggleAndSelectBody(editor, togglePos)
}
