// @vitest-environment jsdom

import { Editor } from '@tiptap/core'
import StarterKit from '@tiptap/starter-kit'
import { NodeSelection, TextSelection } from '@tiptap/pm/state'
import { afterEach, describe, expect, it } from 'vitest'

import {
  BuildinToggle,
  shouldProtectBuildinToggleFromKeyboardDelete,
} from '../../src/components/tasks/richText/extensions/tiptapBuildinToggleExtension'

function makeEditor(content: string): Editor {
  return new Editor({
    extensions: [StarterKit.configure({ heading: false }), BuildinToggle],
    content,
  })
}

/** Позиция начала контента первого toggle в документе. */
function toggleContentStart(editor: Editor): number {
  let pos = -1
  editor.state.doc.descendants((node, p) => {
    if (node.type.name === 'buildinToggle') {
      pos = p
      return false
    }
    return true
  })
  return pos + 1
}

describe('BuildinToggle Backspace/Delete guard', () => {
  let editor: Editor | null = null

  afterEach(() => {
    editor?.destroy()
    editor = null
  })

  it('in the middle of toggle text does NOT allow deleting the whole block', () => {
    editor = makeEditor(
      '<details class="buildin-toggle"><summary>Заголовок</summary><div class="buildin-toggle-body"><p>abc</p></div></details>',
    )
    // Курсор в конец текста «abc» внутри toggle: paragraph open (+1), текст 3 символа
    const start = toggleContentStart(editor)
    editor.commands.setTextSelection(start + 1 + 3)
    expect(shouldProtectBuildinToggleFromKeyboardDelete(editor.state.selection)).toBe(false)
    expect(editor.getHTML()).toContain('abc')
    expect(editor.getHTML()).toContain('buildin-toggle')
  })

  it('at the start of empty toggle Backspace does not delete the block', () => {
    editor = makeEditor(
      '<details class="buildin-toggle"><summary>Заголовок</summary><div class="buildin-toggle-body"><p></p></div></details>',
    )
    const start = toggleContentStart(editor)
    editor.commands.setTextSelection(start + 1)
    expect(shouldProtectBuildinToggleFromKeyboardDelete(editor.state.selection)).toBe(true)
    editor.commands.keyboardShortcut('Backspace')
    expect(editor.getHTML()).toContain('buildin-toggle')
  })

  it('insertBuildinToggle leaves TextSelection in the body, not NodeSelection', () => {
    editor = makeEditor('<p></p>')
    editor.commands.insertBuildinToggle()
    expect(editor.state.selection).toBeInstanceOf(TextSelection)
    expect(editor.state.selection).not.toBeInstanceOf(NodeSelection)
    expect(editor.getHTML()).toContain('buildin-toggle')
  })

  it('deleteBuildinToggle still removes the block', () => {
    editor = makeEditor(
      '<details class="buildin-toggle"><summary>Заголовок</summary><div class="buildin-toggle-body"><p></p></div></details>',
    )
    const start = toggleContentStart(editor)
    editor.commands.setTextSelection(start + 1)
    expect(editor.commands.deleteBuildinToggle()).toBe(true)
    expect(editor.getHTML()).not.toContain('buildin-toggle')
  })

  it('with non-empty selection does NOT allow deleting the whole block', () => {
    editor = makeEditor(
      '<details class="buildin-toggle"><summary>Заголовок</summary><div class="buildin-toggle-body"><p>abc</p></div></details>',
    )
    const start = toggleContentStart(editor)
    const from = start + 1
    const to = start + 1 + 3
    const tr = editor.state.tr.setSelection(TextSelection.create(editor.state.doc, from, to))
    editor.view.dispatch(tr)
    expect(editor.state.selection.empty).toBe(false)
    expect(shouldProtectBuildinToggleFromKeyboardDelete(editor.state.selection)).toBe(false)
  })

  it('outside a toggle does NOT allow deleting', () => {
    editor = makeEditor('<p>текст вне toggle</p>')
    editor.commands.setTextSelection(2)
    expect(shouldProtectBuildinToggleFromKeyboardDelete(editor.state.selection)).toBe(false)
  })
})
