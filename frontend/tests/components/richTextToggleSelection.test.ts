// @vitest-environment jsdom

import { Editor } from '@tiptap/core'
import StarterKit from '@tiptap/starter-kit'
import { afterEach, describe, expect, it } from 'vitest'

import { BuildinToggle } from '@/components/tasks/richText/extensions/tiptapBuildinToggleExtension'
import {
  applyBuildinToggleNativeSelectionFromPm,
  splitToggleBodyOnEnter,
  syncBuildinTogglePmSelectionFromNative,
} from '@/components/tasks/richText/extensions/tiptapBuildinToggleSelection'

function makeEditor(content: string): Editor {
  return new Editor({
    extensions: [StarterKit.configure({ heading: false }), BuildinToggle],
    content,
  })
}

function firstTogglePos(editor: Editor): number {
  let pos = -1
  editor.state.doc.descendants((node, p) => {
    if (node.type.name === 'buildinToggle') {
      pos = p
      return false
    }
    return true
  })
  return pos
}

describe('syncBuildinTogglePmSelectionFromNative', () => {
  let editor: Editor | null = null

  afterEach(() => {
    editor?.destroy()
    editor = null
    document.body.replaceChildren()
  })

  it('подтягивает PM selection к native-каретке в теле toggle, а не к концу документа', () => {
    editor = makeEditor(
      '<p>до</p><details class="buildin-toggle" open="open"><summary>Раздел</summary><div class="buildin-toggle-body"><p>abc</p></div></details><p>после</p>',
    )
    document.body.appendChild(editor.view.dom)
    editor.commands.focus('end')
    const atEnd = editor.state.selection.from

    const contentDOM = editor.view.dom.querySelector('.buildin-toggle-body')
    expect(contentDOM).toBeTruthy()
    const text = contentDOM?.querySelector('p')?.firstChild
    expect(text).toBeTruthy()
    const range = document.createRange()
    range.setStart(text as Text, 1)
    range.collapse(true)
    const sel = window.getSelection()
    sel?.removeAllRanges()
    sel?.addRange(range)

    const togglePos = firstTogglePos(editor)
    const synced = syncBuildinTogglePmSelectionFromNative(editor, contentDOM as HTMLElement, () => togglePos)
    expect(synced).toBe(true)
    expect(editor.state.selection.from).not.toBe(atEnd)
    expect(editor.state.selection.from).toBeGreaterThan(togglePos)
    expect(editor.state.selection.from).toBeLessThan(togglePos + (editor.state.doc.nodeAt(togglePos)?.nodeSize ?? 0))
  })

  it('подтягивает PM selection к native-range в теле toggle, не схлопывая в точку', () => {
    editor = makeEditor(
      '<p>до</p><details class="buildin-toggle" open="open"><summary>Раздел</summary><div class="buildin-toggle-body"><p>abcdef</p></div></details><p>после</p>',
    )
    document.body.appendChild(editor.view.dom)
    editor.commands.focus('end')

    const contentDOM = editor.view.dom.querySelector('.buildin-toggle-body')
    expect(contentDOM).toBeTruthy()
    const text = contentDOM?.querySelector('p')?.firstChild
    expect(text).toBeTruthy()
    const range = document.createRange()
    range.setStart(text as Text, 1)
    range.setEnd(text as Text, 5)
    const sel = window.getSelection()
    sel?.removeAllRanges()
    sel?.addRange(range)

    const togglePos = firstTogglePos(editor)
    const toggleSize = editor.state.doc.nodeAt(togglePos)?.nodeSize ?? 0
    const synced = syncBuildinTogglePmSelectionFromNative(editor, contentDOM as HTMLElement, () => togglePos)
    expect(synced).toBe(true)
    expect(editor.state.selection.from).not.toBe(editor.state.selection.to)
    expect(editor.state.selection.from).toBeGreaterThan(togglePos)
    expect(editor.state.selection.to).toBeLessThan(togglePos + toggleSize)
  })

  it('после splitBlock на непустой строке native-каретка переходит в новый абзац', () => {
    editor = makeEditor(
      '<details class="buildin-toggle" open="open"><summary>Раздел</summary><div class="buildin-toggle-body"><p>abc</p></div></details>',
    )
    document.body.appendChild(editor.view.dom)
    const togglePos = firstTogglePos(editor)
    const contentDOM = editor.view.dom.querySelector('.buildin-toggle-body') as HTMLElement
    const text = contentDOM.querySelector('p')?.firstChild as Text
    const range = document.createRange()
    range.setStart(text, 3)
    range.collapse(true)
    window.getSelection()?.removeAllRanges()
    window.getSelection()?.addRange(range)

    editor.commands.setTextSelection(togglePos + 1 + 1 + 3)
    expect(splitToggleBodyOnEnter(editor)).toBe(true)
    expect(contentDOM.querySelectorAll('p')).toHaveLength(2)

    const applied = applyBuildinToggleNativeSelectionFromPm(editor, contentDOM, () => togglePos)
    expect(applied).toBe(true)
    const anchor = window.getSelection()?.anchorNode ?? null
    const second = contentDOM.querySelectorAll('p')[1]
    expect(anchor).not.toBeNull()
    expect(Boolean(anchor && (second.contains(anchor) || anchor === second))).toBe(true)
  })
})
