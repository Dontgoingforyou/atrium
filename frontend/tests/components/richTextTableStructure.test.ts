// @vitest-environment jsdom

import { Editor } from '@tiptap/core'
import StarterKit from '@tiptap/starter-kit'
import { afterEach, describe, expect, it } from 'vitest'

import { portalTableExtensions } from '@/components/tasks/richText/extensions/tiptapTableExtensions'
import {
  findActiveTableWrapper,
  selectIntoTableWrapper,
} from '@/components/tasks/richText/toolbar/tableFloatingMenuDom'

const HEADER_TABLE =
  '<table><thead><tr><th>h1</th><th>h2</th></tr></thead><tbody><tr><td>a</td><td>b</td></tr></tbody></table>'

const extensions = [
  StarterKit.configure({ heading: false, link: false, underline: false }),
  ...portalTableExtensions,
]

function textNodePos(editor: Editor, text: string): number {
  let pos = -1
  editor.state.doc.descendants((node, nodePos) => {
    if (pos !== -1) return false
    if (node.isText && node.text === text) pos = nodePos
    return pos === -1
  })
  if (pos === -1) throw new Error(`text node "${text}" not found`)
  return pos
}

function placeCaret(editor: Editor, text: string): void {
  editor.commands.setTextSelection(textNodePos(editor, text) + 1)
}

function cellTextAtSelection(editor: Editor): string {
  const $pos = editor.state.doc.resolve(editor.state.selection.from)
  for (let depth = $pos.depth; depth > 0; depth -= 1) {
    const name = $pos.node(depth).type.name
    if (name === 'tableCell' || name === 'tableHeader') return $pos.node(depth).textContent
  }
  return ''
}

function tableGrid(editor: Editor): string[][] {
  const rows: string[][] = []
  editor.state.doc.descendants((node) => {
    if (node.type.name !== 'table') return
    node.forEach((row) => {
      const cells: string[] = []
      row.forEach((cell) => {
        cells.push(cell.textContent)
      })
      rows.push(cells)
    })
    return false
  })
  return rows
}

function mount(content: string): Editor {
  const editor = new Editor({ extensions, content })
  document.body.appendChild(editor.view.dom)
  return editor
}

describe('структура rich-text таблицы', () => {
  let editor: Editor | null = null

  afterEach(() => {
    editor?.destroy()
    editor = null
  })

  it('добавляет столбец справа от ячейки с курсором, а не в начало', () => {
    editor = mount(HEADER_TABLE)
    placeCaret(editor, 'b')
    expect(editor.chain().focus().addColumnAfter().run()).toBe(true)
    expect(tableGrid(editor)).toEqual([
      ['h1', 'h2', ''],
      ['a', 'b', ''],
    ])
  })

  it('добавляет строку сразу под строкой с курсором', () => {
    editor = mount(HEADER_TABLE)
    placeCaret(editor, 'b')
    expect(editor.chain().focus().addRowAfter().run()).toBe(true)
    expect(tableGrid(editor)).toEqual([
      ['h1', 'h2'],
      ['a', 'b'],
      ['', ''],
    ])
  })

  it('selectIntoTableWrapper не переносит курсор из последней ячейки в первую', () => {
    editor = mount('<p>до</p>' + HEADER_TABLE)
    placeCaret(editor, 'b')
    const wrapper = findActiveTableWrapper(editor)
    expect(wrapper).not.toBeNull()
    const caret = editor.state.selection.from
    expect(selectIntoTableWrapper(editor, wrapper!)).toBe(true)
    expect(editor.state.selection.from).toBe(caret)
    expect(cellTextAtSelection(editor)).toBe('b')
  })

  it('selectIntoTableWrapper с курсором вне таблицы ставит его в последнюю ячейку', () => {
    editor = mount('<p>до</p>' + HEADER_TABLE)
    placeCaret(editor, 'b')
    const wrapper = findActiveTableWrapper(editor)
    expect(wrapper).not.toBeNull()
    placeCaret(editor, 'до')
    expect(editor.isActive('table')).toBe(false)
    expect(selectIntoTableWrapper(editor, wrapper!)).toBe(true)
    expect(cellTextAtSelection(editor)).toBe('b')
    expect(editor.chain().focus().addColumnAfter().run()).toBe(true)
    expect(tableGrid(editor)).toEqual([
      ['h1', 'h2', ''],
      ['a', 'b', ''],
    ])
  })

  it('удаляет столбец, в котором стоит курсор, и оставляет соседний текст', () => {
    editor = mount(HEADER_TABLE)
    placeCaret(editor, 'b')
    expect(editor.chain().focus().deleteColumn().run()).toBe(true)
    expect(tableGrid(editor)).toEqual([['h1'], ['a']])
  })

  it('сдвигает столбец вправо и сохраняет порядок после повторного открытия HTML', () => {
    editor = mount(HEADER_TABLE)
    placeCaret(editor, 'a')
    expect(editor.chain().focus().moveColumnRight().run()).toBe(true)
    expect(tableGrid(editor)).toEqual([
      ['h2', 'h1'],
      ['b', 'a'],
    ])
    const html = editor.getHTML()
    const reopened = new Editor({ extensions, content: html })
    expect(tableGrid(reopened)).toEqual([
      ['h2', 'h1'],
      ['b', 'a'],
    ])
    reopened.destroy()
  })

  it('один столбец и ячейка на всю ширину не стирают таблицу', () => {
    editor = mount('<table><tbody><tr><td>only</td></tr></tbody></table>')
    placeCaret(editor, 'only')
    expect(() => {
      editor!.chain().focus().deleteColumn().run()
      editor!.chain().focus().moveColumnLeft().run()
      editor!.chain().focus().moveColumnRight().run()
    }).not.toThrow()
    expect(tableGrid(editor)).toEqual([['only']])

    editor.destroy()
    editor = mount(
      '<table><tbody><tr><td colspan="2">wide</td></tr><tr><td>a</td><td>b</td></tr></tbody></table>',
    )
    placeCaret(editor, 'wide')
    expect(() => {
      editor!.chain().focus().deleteColumn().run()
      editor!.chain().focus().moveColumnLeft().run()
      editor!.chain().focus().moveColumnRight().run()
    }).not.toThrow()
    expect(editor.getText()).toContain('wide')
    expect(editor.getText()).toContain('a')
    expect(editor.getText()).toContain('b')
  })
})
