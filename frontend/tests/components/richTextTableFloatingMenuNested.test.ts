// @vitest-environment jsdom

import { Editor } from '@tiptap/core'
import StarterKit from '@tiptap/starter-kit'
import { afterEach, describe, expect, it } from 'vitest'

import { portalTableExtensions } from '@/components/tasks/richText/extensions/tiptapTableExtensions'
import {
  findActiveTableWrapper,
  findOrCreateTableFloatSlot,
  findTableWrapperFromTarget,
  resolveTableFloatWrapper,
  selectIntoTableWrapper,
} from '@/components/tasks/richText/toolbar/tableFloatingMenuDom'

// Внешняя таблица 2×2, во внутренней ячейке первой строки — вложенная таблица 2×2.
const NESTED_TABLE_HTML =
  '<table><tbody>' +
  '<tr>' +
  '<td><table><tbody><tr><td>inner1</td><td>inner2</td></tr></tbody></table></td>' +
  '<td>outer-r1-c2</td>' +
  '</tr>' +
  '<tr><td>outer-r2-c1</td><td>outer-r2-c2</td></tr>' +
  '</tbody></table>'

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

describe('вложенные таблицы: floating «⋯» переключается между внутренней и внешней таблицей', () => {
  let editor: Editor | null = null

  afterEach(() => {
    editor?.destroy()
    editor = null
  })

  it('findActiveTableWrapper находит именно ту обёртку, где сейчас курсор', () => {
    editor = new Editor({
      extensions: [StarterKit.configure({ heading: false, link: false, underline: false }), ...portalTableExtensions],
      content: NESTED_TABLE_HTML,
    })
    document.body.appendChild(editor.view.dom)

    editor.commands.setTextSelection(textNodePos(editor, 'inner1') + 1)
    const innerWrapper = findActiveTableWrapper(editor)
    expect(innerWrapper).not.toBeNull()
    const innerTable = innerWrapper!.querySelector(':scope > table') as HTMLTableElement | null
    expect(innerTable?.rows.length).toBe(1)
    expect(innerTable?.rows[0]?.cells.length).toBe(2)

    editor.commands.setTextSelection(textNodePos(editor, 'outer-r2-c1') + 1)
    const outerWrapper = findActiveTableWrapper(editor)
    expect(outerWrapper).not.toBeNull()
    const outerTable = outerWrapper!.querySelector(':scope > table') as HTMLTableElement | null
    expect(outerTable?.rows.length).toBe(2)
    expect(outerWrapper).not.toBe(innerWrapper)
    // Внешняя обёртка физически содержит внутреннюю (вложенная таблица).
    expect(outerWrapper!.contains(innerWrapper!)).toBe(true)
  })

  it('findOrCreateTableFloatSlot создаёт слот СВОЕЙ обёртки, а не переиспользует слот вложенной таблицы', () => {
    editor = new Editor({
      extensions: [StarterKit.configure({ heading: false, link: false, underline: false }), ...portalTableExtensions],
      content: NESTED_TABLE_HTML,
    })
    document.body.appendChild(editor.view.dom)

    editor.commands.setTextSelection(textNodePos(editor, 'inner1') + 1)
    const innerWrapper = findActiveTableWrapper(editor)!
    const innerSlot = findOrCreateTableFloatSlot(innerWrapper, 'slot')

    editor.commands.setTextSelection(textNodePos(editor, 'outer-r2-c1') + 1)
    const outerWrapper = findActiveTableWrapper(editor)!
    const outerSlot = findOrCreateTableFloatSlot(outerWrapper, 'slot')

    // Регрессия: без :scope querySelector('[data-table-float-slot]') от внешней
    // обёртки нашёл бы слот, вложенный глубоко внутри неё (слот внутренней
    // таблицы), и «⋯» навсегда прилипал бы к внутренней таблице.
    expect(outerSlot).not.toBe(innerSlot)
    expect(outerSlot.parentElement).toBe(outerWrapper)
    expect(innerSlot.parentElement).toBe(innerWrapper)

    // Повторный вызов для той же обёртки переиспользует уже созданный слот.
    expect(findOrCreateTableFloatSlot(outerWrapper, 'slot')).toBe(outerSlot)
  })

  it('findTableWrapperFromTarget берёт обёртку по DOM, без курсора в ячейке', () => {
    const wrapper = document.createElement('div')
    wrapper.className = 'tableWrapper'
    const td = document.createElement('td')
    const text = document.createTextNode('ячейка')
    td.appendChild(text)
    wrapper.appendChild(td)
    expect(findTableWrapperFromTarget(text)).toBe(wrapper)
    expect(findTableWrapperFromTarget(null)).toBeNull()
    expect(findTableWrapperFromTarget(document.createElement('p'))).toBeNull()
  })

  it('resolveTableFloatWrapper показывает меню по наведению, даже если курсор вне таблицы', () => {
    editor = new Editor({
      extensions: [StarterKit.configure({ heading: false, link: false, underline: false }), ...portalTableExtensions],
      content: '<p>до</p>' + NESTED_TABLE_HTML,
    })
    document.body.appendChild(editor.view.dom)
    editor.commands.setTextSelection(2)
    expect(editor.isActive('table')).toBe(false)

    editor.commands.setTextSelection(textNodePos(editor, 'outer-r2-c1') + 1)
    const wrapper = findActiveTableWrapper(editor)
    expect(wrapper).not.toBeNull()
    editor.commands.setTextSelection(2)
    expect(editor.isActive('table')).toBe(false)
    const cell = Array.from(wrapper!.querySelectorAll('td')).find((td) => td.textContent === 'outer-r2-c1')
    expect(cell).toBeInstanceOf(HTMLElement)
    const event = new MouseEvent('mousemove')
    Object.defineProperty(event, 'target', { value: cell })
    expect(resolveTableFloatWrapper(editor, event)).toBe(wrapper)
    expect(resolveTableFloatWrapper(editor, null)).toBeNull()
  })

  it('selectIntoTableWrapper ставит выделение в таблицу для команд меню', () => {
    editor = new Editor({
      extensions: [StarterKit.configure({ heading: false, link: false, underline: false }), ...portalTableExtensions],
      content: '<p>до</p>' + NESTED_TABLE_HTML,
    })
    document.body.appendChild(editor.view.dom)
    editor.commands.setTextSelection(textNodePos(editor, 'outer-r2-c1') + 1)
    const wrapper = findActiveTableWrapper(editor)
    expect(wrapper).not.toBeNull()
    editor.commands.setTextSelection(2)
    expect(editor.isActive('table')).toBe(false)
    expect(selectIntoTableWrapper(editor, wrapper!)).toBe(true)
    expect(editor.isActive('table')).toBe(true)
  })
})
