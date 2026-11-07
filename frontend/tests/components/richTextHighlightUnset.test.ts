// @vitest-environment jsdom

import { Editor } from '@tiptap/core'
import Document from '@tiptap/extension-document'
import Highlight from '@tiptap/extension-highlight'
import Paragraph from '@tiptap/extension-paragraph'
import Text from '@tiptap/extension-text'
import { describe, expect, it } from 'vitest'

import { RICH_TEXT_DEFAULT_HIGHLIGHT_COLOR } from '../../src/components/tasks/richText/constants'
import { PortalHighlight } from '../../src/components/tasks/richText/extensions/portalHighlight'

function createHighlightEditor(html: string): Editor {
  return new Editor({
    extensions: [Document, Paragraph, Text, Highlight.configure({ multicolor: true })],
    content: html,
  })
}

function createPortalHighlightEditor(html = '<p>мяу</p>'): Editor {
  return new Editor({
    extensions: [Document, Paragraph, Text, PortalHighlight],
    content: html,
  })
}

describe('unsetHighlight с extendMarkRange', () => {
  it('снимает заливку при свёрнутом курсоре внутри mark', () => {
    const editor = createHighlightEditor(
      '<p><mark data-color="#fef08a" style="background-color: #fef08a">мяу</mark></p>',
    )
    // Курсор в середине слова «мяу» (после первого символа mark-текста)
    editor.commands.setTextSelection(2)

    editor.chain().focus().extendMarkRange('highlight').unsetHighlight().run()

    expect(editor.getHTML()).not.toContain('<mark')
    expect(editor.getHTML()).toContain('мяу')
    editor.destroy()
  })

  it('без extendMarkRange заливка остаётся при пустой selection', () => {
    const editor = createHighlightEditor(
      '<p><mark data-color="#fef08a" style="background-color: #fef08a">мяу</mark></p>',
    )
    editor.commands.setTextSelection(2)

    editor.chain().focus().unsetHighlight().run()

    expect(editor.getHTML()).toContain('<mark')
    editor.destroy()
  })
})

describe('PortalHighlight default color', () => {
  it('setHighlight с дефолтным цветом пишет background-color', () => {
    const editor = createPortalHighlightEditor()
    editor.commands.setTextSelection({ from: 1, to: 4 })
    editor.chain().focus().setHighlight({ color: RICH_TEXT_DEFAULT_HIGHLIGHT_COLOR }).run()

    const html = editor.getHTML()
    expect(html).toContain('<mark')
    expect(html).toContain('background-color')
    expect(html.toLowerCase()).toContain(RICH_TEXT_DEFAULT_HIGHLIGHT_COLOR.toLowerCase())
    editor.destroy()
  })

  it('toggleHighlight через shortcut-команду всегда с цветом по умолчанию', () => {
    const editor = createPortalHighlightEditor()
    editor.commands.setTextSelection({ from: 1, to: 4 })
    editor.commands.toggleHighlight({ color: RICH_TEXT_DEFAULT_HIGHLIGHT_COLOR })

    const html = editor.getHTML()
    expect(html).toContain('background-color')
    expect(html.toLowerCase()).toContain(RICH_TEXT_DEFAULT_HIGHLIGHT_COLOR.toLowerCase())
    editor.destroy()
  })
})
