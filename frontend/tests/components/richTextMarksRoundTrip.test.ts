// @vitest-environment jsdom

import { Editor } from '@tiptap/core'
import StarterKit from '@tiptap/starter-kit'
import Heading from '@tiptap/extension-heading'
import TextAlign from '@tiptap/extension-text-align'
import Underline from '@tiptap/extension-underline'
import Link from '@tiptap/extension-link'
import Highlight from '@tiptap/extension-highlight'
import TaskList from '@tiptap/extension-task-list'
import { TaskItem } from '@tiptap/extension-list'
import { Color } from '@tiptap/extension-color'
import { TextStyle } from '@tiptap/extension-text-style'
import { afterEach, describe, expect, it } from 'vitest'

import { FontSize } from '../../src/components/tasks/richText/extensions/tiptapFontSizeExtension'
import { LineHeight } from '../../src/components/tasks/richText/extensions/tiptapLineHeightExtension'
import { BuildinToggle } from '../../src/components/tasks/richText/extensions/tiptapBuildinToggleExtension'
import { portalTableExtensions } from '../../src/components/tasks/richText/extensions/tiptapTableExtensions'

describe('richText marks round-trip', () => {
  let editor: Editor | null = null

  afterEach(() => {
    editor?.destroy()
    editor = null
  })

  it('preserves underline, link, highlight and justify', () => {
    const input =
      '<p style="text-align: justify"><a href="https://example.com"><u>Текст</u></a> <mark data-color="#fef08a" style="background-color: #fef08a">маркер</mark></p>'
    editor = new Editor({
      extensions: [
        StarterKit.configure({ heading: false, link: false, underline: false }),
        Heading.configure({ levels: [1, 2, 3] }),
        TextAlign.configure({ types: ['heading', 'paragraph'], alignments: ['left', 'center', 'right', 'justify'] }),
        TextStyle,
        FontSize,
        Color,
        Underline,
        Highlight.configure({ multicolor: true }),
        Link.configure({ openOnClick: false }),
        TaskList,
        TaskItem,
        LineHeight,
        BuildinToggle,
        ...portalTableExtensions,
      ],
      content: input,
    })
    const html = editor.getHTML()
    expect(html).toContain('text-align: justify')
    expect(html).toContain('href="https://example.com"')
    expect(html).toContain('<u>')
    expect(html).toContain('background-color')
  })
})
