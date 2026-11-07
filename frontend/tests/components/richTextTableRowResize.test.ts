// @vitest-environment jsdom

import { Editor } from '@tiptap/core'
import StarterKit from '@tiptap/starter-kit'
import { afterEach, describe, expect, it } from 'vitest'

import { portalTableExtensions } from '../../src/components/tasks/richText/extensions/tiptapTableExtensions'

const TABLE_HTML =
  '<table><tbody>' +
  '<tr><td>a1</td><td>a2</td></tr>' +
  '<tr><td>b1</td><td>b2</td></tr>' +
  '<tr><td>c1</td><td>c2</td></tr>' +
  '</tbody></table>'

function mockRect(el: Element, rect: { top: number; bottom: number; left: number; right: number }) {
  ;(el as HTMLElement).getBoundingClientRect = () =>
    ({
      top: rect.top,
      bottom: rect.bottom,
      left: rect.left,
      right: rect.right,
      width: rect.right - rect.left,
      height: rect.bottom - rect.top,
      x: rect.left,
      y: rect.top,
      toJSON() {
        return this
      },
    }) as DOMRect
}

describe('протяжка высоты строки таблицы (TableRowResize)', () => {
  let editor: Editor | null = null

  afterEach(() => {
    editor?.destroy()
    editor = null
  })

  it('после mousedown у нижнего края + drag сохраняет height в атрибутах строки', () => {
    editor = new Editor({
      extensions: [StarterKit.configure({ heading: false, link: false, underline: false }), ...portalTableExtensions],
      content: TABLE_HTML,
    })

    const dom = editor.view.dom
    document.body.appendChild(dom)

    const firstRowCell = dom.querySelector('tr:nth-child(1) td:nth-child(1)') as HTMLTableCellElement
    const secondRowCell = dom.querySelector('tr:nth-child(2) td:nth-child(1)') as HTMLTableCellElement
    expect(firstRowCell).toBeInstanceOf(HTMLTableCellElement)
    expect(secondRowCell).toBeInstanceOf(HTMLTableCellElement)

    // Строка 1: y от 0 до 30 (низ на y=30). Курсор X далеко от правого края (не column-resize).
    mockRect(firstRowCell, { top: 0, bottom: 30, left: 0, right: 100 })
    mockRect(secondRowCell, { top: 30, bottom: 60, left: 0, right: 100 })
    mockRect(firstRowCell.closest('tr')!, { top: 0, bottom: 30, left: 0, right: 200 })

    firstRowCell.dispatchEvent(
      new MouseEvent('mousedown', { bubbles: true, cancelable: true, clientX: 50, clientY: 29, button: 0 }),
    )
    window.dispatchEvent(new MouseEvent('pointermove', { bubbles: true, clientY: 79 }))
    window.dispatchEvent(new MouseEvent('pointerup', { bubbles: true }))

    const rowNode = editor.state.doc.firstChild?.firstChild
    expect(rowNode?.attrs.height).toBe('80px')
    // Протяжка строки не должна конфликтовать с tableEditing и создавать CellSelection.
    expect(editor.state.selection.constructor.name).not.toBe('CellSelection')
  })
})
