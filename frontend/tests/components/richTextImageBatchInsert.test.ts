// @vitest-environment jsdom

import { Editor } from '@tiptap/core'
import StarterKit from '@tiptap/starter-kit'
import { afterEach, describe, expect, it } from 'vitest'

import {
  DocumentImage,
  insertDocumentImageAt,
} from '../../src/components/tasks/richText/extensions/tiptapImageExtension'

describe('вставка нескольких картинок за один батч (uploadAndInsertRichTextImages)', () => {
  let editor: Editor | null = null

  afterEach(() => {
    editor?.destroy()
    editor = null
  })

  function insertBatch(content: string, initialPos: number, count: number) {
    editor = new Editor({
      extensions: [StarterKit.configure({ heading: false, link: false, underline: false }), DocumentImage],
      content,
    })
    let pos = initialPos
    for (let i = 1; i <= count; i += 1) {
      pos = insertDocumentImageAt(editor, pos, `img${i}.png`)
    }
    return editor.getHTML()
  }

  it('сохраняет все картинки при вставке ВЫШЕ текста (в начало документа)', () => {
    const html = insertBatch('<p>Текст документа</p>', 0, 3)
    expect(html).toContain('img1.png')
    expect(html).toContain('img2.png')
    expect(html).toContain('img3.png')
  })

  it('сохраняет все картинки при вставке НИЖЕ текста (в конец документа)', () => {
    const content = '<p>Текст документа</p>'
    editor = new Editor({
      extensions: [StarterKit.configure({ heading: false, link: false, underline: false }), DocumentImage],
      content,
    })
    const endPos = editor.state.doc.content.size
    let pos = endPos
    pos = insertDocumentImageAt(editor, pos, 'img1.png')
    pos = insertDocumentImageAt(editor, pos, 'img2.png')
    insertDocumentImageAt(editor, pos, 'img3.png')
    const html = editor.getHTML()
    expect(html).toContain('img1.png')
    expect(html).toContain('img2.png')
    expect(html).toContain('img3.png')
  })

  it('сохраняет все картинки в пустом документе', () => {
    const html = insertBatch('<p></p>', 0, 2)
    expect(html).toContain('img1.png')
    expect(html).toContain('img2.png')
  })
})
