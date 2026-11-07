// @vitest-environment jsdom

import { Editor } from '@tiptap/core'
import StarterKit from '@tiptap/starter-kit'
import { columnResizingPluginKey } from '@tiptap/pm/tables'
import { afterEach, describe, expect, it } from 'vitest'

import { portalTableExtensions } from '../../src/components/tasks/richText/extensions/tiptapTableExtensions'

const TABLE_HTML = '<table><tbody><tr><td>a1</td><td>a2</td></tr></tbody></table>'

describe('columnResizing не рисует widget-декорацию при наведении на границу колонки', () => {
  let editor: Editor | null = null

  afterEach(() => {
    editor?.destroy()
    editor = null
  })

  it('setHandle не добавляет .column-resize-handle в DOM (иначе Chromium «прыгает» высотой строки)', () => {
    editor = new Editor({
      extensions: [StarterKit.configure({ heading: false, link: false, underline: false }), ...portalTableExtensions],
      content: TABLE_HTML,
    })

    let firstCellPos = -1
    editor.state.doc.descendants((node, pos) => {
      if (firstCellPos === -1 && node.type.name === 'tableCell') firstCellPos = pos
      return firstCellPos === -1
    })

    editor.view.dispatch(editor.state.tr.setMeta(columnResizingPluginKey, { setHandle: firstCellPos }))

    expect(editor.view.dom.querySelectorAll('.column-resize-handle').length).toBe(0)
    // Курсор при этом всё равно должен переключаться в режим ресайза колонки.
    expect(editor.view.dom.className).toContain('resize-cursor')
  })
})
