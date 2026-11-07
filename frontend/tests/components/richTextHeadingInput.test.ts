// @vitest-environment jsdom

import { Editor } from '@tiptap/core'
import Heading from '@tiptap/extension-heading'
import StarterKit from '@tiptap/starter-kit'
import { afterEach, describe, expect, it } from 'vitest'

function makeEditor(content: string): Editor {
  return new Editor({
    extensions: [StarterKit.configure({ heading: false }), Heading.configure({ levels: [1, 2, 3] })],
    content,
  })
}

describe('heading посимвольный ввод', () => {
  let editor: Editor | null = null

  afterEach(() => {
    editor?.destroy()
    editor = null
  })

  it('несколько вставок остаются в том же H1, не в следующем абзаце', () => {
    editor = makeEditor('<h1></h1>')
    editor.commands.focus('end')
    for (const ch of 'Hello') {
      editor.commands.insertContent(ch)
    }
    expect(editor.getHTML()).toContain('<h1>Hello</h1>')
    expect(editor.getHTML()).not.toMatch(/<h1>H<\/h1>\s*<p>/)
    expect(editor.isActive('heading', { level: 1 })).toBe(true)
  })
})
