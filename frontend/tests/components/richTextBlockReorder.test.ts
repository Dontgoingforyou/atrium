// @vitest-environment jsdom

import { Editor } from '@tiptap/core'
import { TaskItem } from '@tiptap/extension-list'
import TaskList from '@tiptap/extension-task-list'
import StarterKit from '@tiptap/starter-kit'
import { afterEach, describe, expect, it } from 'vitest'

import { BuildinToggle } from '@/components/tasks/richText/extensions/tiptapBuildinToggleExtension'
import {
  applyBlockReorder,
  BlockReorder,
  collectSiblingBlockRanges,
  findMovableBlockRange,
  findTableAncestorBlockRange,
  findToggleAncestorBlockRange,
  isDropInSameReorderGroup,
  shouldUseSiblingBlockReorder,
} from '@/components/tasks/richText/extensions/tiptapBlockReorderExtension'
import { portalTableExtensions } from '@/components/tasks/richText/extensions/tiptapTableExtensions'
import {
  BLOCK_REORDER_HANDLE_ATTR,
  isBlockReorderExemptTarget,
  isBlockReorderHandleTarget,
  isTableReorderTarget,
  isBuildinToggleChromeTarget,
  isToggleBodyReorderTarget,
  isToggleHeaderReorderTarget,
  isToggleSummaryTarget,
  preferToggleAncestorForPointerTarget,
  resolveBlockReorderHandleEl,
} from '@/domain/documents/richTextBlockReorder'

function makeEditor(content: string): Editor {
  return new Editor({
    extensions: [
      StarterKit.configure({ heading: false }),
      BuildinToggle,
      BlockReorder,
      ...portalTableExtensions,
    ],
    content,
  })
}

function textPos(editor: Editor, text: string): number {
  let innerPos = -1
  editor.state.doc.descendants((node, pos) => {
    if (node.isText && node.text === text) {
      innerPos = pos
      return false
    }
    return true
  })
  return innerPos
}

function taskItemNode(text: string) {
  return {
    type: 'taskItem' as const,
    attrs: { checked: false },
    content: [{ type: 'paragraph' as const, content: [{ type: 'text' as const, text }] }],
  }
}

function makeTaskListEditor(
  itemTexts: string[] = ['первый', 'второй'],
  after: Record<string, unknown>[] = [],
): Editor {
  return new Editor({
    extensions: [
      StarterKit.configure({ heading: false }),
      TaskList.configure({ HTMLAttributes: { class: 'buildin-task-list' } }),
      TaskItem.configure({
        nested: true,
        HTMLAttributes: { class: 'buildin-task-item' },
      }),
      BlockReorder,
    ],
    content: {
      type: 'doc',
      content: [
        {
          type: 'taskList',
          content: itemTexts.map((text) => taskItemNode(text)),
        },
        ...after,
      ],
    },
  })
}

describe('BlockReorder', () => {
  let editor: Editor | null = null

  afterEach(() => {
    editor?.destroy()
    editor = null
  })

  it('меняет местами два соседних абзаца', () => {
    editor = makeEditor('<p>первый</p><p>второй</p>')
    const first = editor.state.doc.child(0)
    const moved = applyBlockReorder(editor.view, 0, first.nodeSize, editor.state.doc.content.size)
    expect(moved).toBe(true)
    expect(editor.getHTML()).toBe('<p>второй</p><p>первый</p>')
  })

  it('Alt+ArrowDown переставляет текущий блок с соседом ниже', () => {
    editor = makeEditor('<p>первый</p><p>второй</p>')
    editor.commands.setTextSelection(2)
    expect(editor.commands.moveRichTextBlock('down')).toBe(true)
    expect(editor.getHTML()).toBe('<p>второй</p><p>первый</p>')
  })

  it('для текста внутри раздела берёт сам абзац, а не весь toggle', () => {
    editor = makeEditor(
      '<details class="buildin-toggle"><summary>Раздел</summary><div class="buildin-toggle-body"><p>внутри</p></div></details>',
    )
    let innerPos = -1
    editor.state.doc.descendants((node, pos) => {
      if (node.isText && node.text === 'внутри') {
        innerPos = pos
        return false
      }
      return true
    })
    const range = findMovableBlockRange(editor.state.doc, innerPos)
    expect(range).not.toBeNull()
    const node = editor.state.doc.nodeAt(range!.from)
    expect(node?.type.name).toBe('paragraph')
  })

  it('для текста в чеклисте берёт весь taskItem, а не внутренний абзац', () => {
    editor = makeTaskListEditor()
    const innerPos = textPos(editor, 'первый')
    expect(innerPos).toBeGreaterThanOrEqual(0)
    const range = findMovableBlockRange(editor.state.doc, innerPos)
    expect(range).not.toBeNull()
    expect(editor.state.doc.nodeAt(range!.from)?.type.name).toBe('taskItem')
    const siblings = collectSiblingBlockRanges(editor.state.doc, range!.from)
    expect(siblings).toHaveLength(2)
    const last = siblings![1]!
    const moved = applyBlockReorder(editor.view, range!.from, range!.size, last.from + last.size)
    expect(moved).toBe(true)
    expect(editor.getText().replace(/\n+/g, '\n').trim()).toBe('второй\nпервый')
  })

  it('одиночный чеклист едет целиком относительно соседнего абзаца', () => {
    editor = makeTaskListEditor(['пункт'], [
      { type: 'paragraph', content: [{ type: 'text', text: 'абзац' }] },
    ])
    const range = findMovableBlockRange(editor.state.doc, textPos(editor, 'пункт'))
    expect(range).not.toBeNull()
    expect(editor.state.doc.nodeAt(range!.from)?.type.name).toBe('taskList')
    const moved = applyBlockReorder(editor.view, range!.from, range!.size, editor.state.doc.content.size)
    expect(moved).toBe(true)
    expect(editor.getText().replace(/\n+/g, '\n').trim()).toBe('абзац\nпункт')
  })

  it('drop на ul оставляет пункт среди соседей, за пределы — выносит обёрнутым списком', () => {
    editor = makeTaskListEditor()
    const doc = editor.state.doc
    const list = doc.child(0)
    expect(list.type.name).toBe('taskList')
    const overList = findMovableBlockRange(doc, 0)
    expect(doc.nodeAt(overList!.from)?.type.name).toBe('taskItem')
    const item = overList!
    expect(isDropInSameReorderGroup(doc, item.from, 0)).toBe(true)
    expect(shouldUseSiblingBlockReorder(doc, item.from, 0)).toBe(true)
    expect(shouldUseSiblingBlockReorder(doc, item.from, doc.content.size)).toBe(false)
    expect(applyBlockReorder(editor.view, item.from, item.size, doc.content.size)).toBe(true)
    expect(editor.getText().replace(/\n+/g, '\n').trim()).toBe('второй\nпервый')
    expect(editor.state.doc.child(0).type.name).toBe('taskList')
    expect(editor.state.doc.child(1).type.name).toBe('taskList')
    expect(editor.state.doc.child(0).textContent).toBe('второй')
    expect(editor.state.doc.child(1).textContent).toBe('первый')
  })

  it.each([
    ['маркеры', '<ul><li><p>первый</p></li><li><p>второй</p></li></ul>'],
    ['нумерацию', '<ol><li><p>первый</p></li><li><p>второй</p></li></ol>'],
  ] as const)('для текста в списке с %s берёт listItem, а не внутренний абзац', (_label, html) => {
    editor = makeEditor(html)
    const innerPos = textPos(editor, 'первый')
    expect(innerPos).toBeGreaterThanOrEqual(0)
    const range = findMovableBlockRange(editor.state.doc, innerPos)
    expect(range).not.toBeNull()
    expect(editor.state.doc.nodeAt(range!.from)?.type.name).toBe('listItem')
    const siblings = collectSiblingBlockRanges(editor.state.doc, range!.from)
    expect(siblings).toHaveLength(2)
    const last = siblings![1]!
    const moved = applyBlockReorder(editor.view, range!.from, range!.size, last.from + last.size)
    expect(moved).toBe(true)
    expect(editor.getText().replace(/\n+/g, '\n').trim()).toBe('второй\nпервый')
  })

  it('drop за пределы маркированного списка выносит пункт обёрнутым ul', () => {
    editor = makeEditor('<ul><li><p>первый</p></li><li><p>второй</p></li></ul>')
    const doc = editor.state.doc
    const overList = findMovableBlockRange(doc, 0)
    expect(doc.nodeAt(overList!.from)?.type.name).toBe('listItem')
    const item = overList!
    expect(shouldUseSiblingBlockReorder(doc, item.from, doc.content.size)).toBe(false)
    expect(applyBlockReorder(editor.view, item.from, item.size, doc.content.size)).toBe(true)
    expect(editor.getText().replace(/\n+/g, '\n').trim()).toBe('второй\nпервый')
    expect(editor.state.doc.child(0).type.name).toBe('bulletList')
    expect(editor.state.doc.child(1).type.name).toBe('bulletList')
    expect(editor.state.doc.child(0).textContent).toBe('второй')
    expect(editor.state.doc.child(1).textContent).toBe('первый')
  })

  it('для заголовка раздела берёт весь toggle', () => {
    editor = makeEditor(
      '<p>до</p><details class="buildin-toggle"><summary>Раздел</summary><div class="buildin-toggle-body"><p>внутри</p></div></details>',
    )
    let innerPos = -1
    editor.state.doc.descendants((node, pos) => {
      if (node.isText && node.text === 'внутри') {
        innerPos = pos
        return false
      }
      return true
    })
    const range = findToggleAncestorBlockRange(editor.state.doc, innerPos)
    expect(range).not.toBeNull()
    expect(editor.state.doc.nodeAt(range!.from)?.type.name).toBe('buildinToggle')
  })

  it('собирает диапазоны соседних top-level блоков', () => {
    editor = makeEditor('<p>A</p><p>B</p><p>C</p>')
    const ranges = collectSiblingBlockRanges(editor.state.doc, 0)
    expect(ranges).toHaveLength(3)
    expect(ranges?.[0]?.from).toBe(0)
    expect(ranges?.[1]?.from).toBe(ranges![0]!.size)
  })

  it('не переставляет блок с поля заголовка раздела', () => {
    const input = document.createElement('input')
    input.className = 'buildin-toggle-title-input'
    expect(isBlockReorderExemptTarget(input)).toBe(true)
    expect(isBlockReorderExemptTarget(document.createElement('p'))).toBe(false)
  })

  it('считает поле заголовка раздела шапкой toggle', () => {
    const input = document.createElement('input')
    input.className = 'buildin-toggle-title-input'
    const header = document.createElement('div')
    header.className = 'buildin-toggle-header'
    const root = document.createElement('div')
    root.className = 'buildin-toggle'
    header.appendChild(input)
    root.appendChild(header)
    document.body.appendChild(root)
    expect(isToggleSummaryTarget(input)).toBe(true)
    expect(isBlockReorderExemptTarget(input)).toBe(true)
    expect(isToggleHeaderReorderTarget(input)).toBe(true)
    expect(isToggleHeaderReorderTarget(header)).toBe(true)
    const del = document.createElement('button')
    del.className = 'buildin-toggle-delete'
    header.appendChild(del)
    expect(isToggleHeaderReorderTarget(del)).toBe(false)
    expect(isBuildinToggleChromeTarget(input)).toBe(true)
    expect(isBuildinToggleChromeTarget(header)).toBe(true)
    expect(isBuildinToggleChromeTarget(document.createElement('p'))).toBe(false)
    const body = document.createElement('div')
    body.className = 'buildin-toggle-body'
    const line = document.createElement('p')
    line.textContent = 'внутри'
    body.appendChild(line)
    root.appendChild(body)
    expect(isToggleBodyReorderTarget(line)).toBe(true)
    expect(preferToggleAncestorForPointerTarget(header)).toBe(true)
    expect(preferToggleAncestorForPointerTarget(input)).toBe(true)
    expect(preferToggleAncestorForPointerTarget(line)).toBe(false)
    root.remove()
  })

  it('распознаёт ручку перестановки и её потомка', () => {
    const handle = document.createElement('div')
    handle.setAttribute(BLOCK_REORDER_HANDLE_ATTR, '')
    const grip = document.createElement('span')
    handle.appendChild(grip)
    expect(isBlockReorderHandleTarget(handle)).toBe(true)
    expect(isBlockReorderHandleTarget(grip)).toBe(true)
    expect(isBlockReorderHandleTarget(document.createElement('p'))).toBe(false)
  })

  it('для ячейки таблицы берёт всю таблицу, а не абзац внутри', () => {
    editor = makeEditor(
      '<p>до</p><table><tr><th>Имя</th></tr><tr><td>Александр</td></tr></table>',
    )
    let innerPos = -1
    editor.state.doc.descendants((node, pos) => {
      if (node.isText && node.text === 'Александр') {
        innerPos = pos
        return false
      }
      return true
    })
    expect(innerPos).toBeGreaterThanOrEqual(0)
    const tableRange = findTableAncestorBlockRange(editor.state.doc, innerPos)
    expect(tableRange).not.toBeNull()
    expect(editor.state.doc.nodeAt(tableRange!.from)?.type.name).toBe('table')
    const cellRange = findMovableBlockRange(editor.state.doc, innerPos)
    expect(cellRange?.from).not.toBe(tableRange?.from)
  })

  it('для .tableWrapper якорит ручку по <table>, не по padding обёртки', () => {
    const wrapper = document.createElement('div')
    wrapper.className = 'tableWrapper'
    wrapper.style.paddingTop = '34px'
    const table = document.createElement('table')
    wrapper.appendChild(table)
    document.body.appendChild(wrapper)
    expect(resolveBlockReorderHandleEl(wrapper)).toBe(table)
    expect(resolveBlockReorderHandleEl(table)).toBe(table)
    wrapper.remove()
  })

  it('для пункта чеклиста якорит ручку по <li>, не по внутреннему <p>', () => {
    const list = document.createElement('ul')
    list.className = 'buildin-task-list'
    const item = document.createElement('li')
    item.className = 'buildin-task-item'
    const paragraph = document.createElement('p')
    paragraph.textContent = 'пункт'
    item.appendChild(paragraph)
    list.appendChild(item)
    document.body.appendChild(list)
    expect(resolveBlockReorderHandleEl(paragraph)).toBe(item)
    expect(resolveBlockReorderHandleEl(item)).toBe(item)
    list.remove()
  })

  it('для обычного пункта списка якорит ручку по <li>, не по внутреннему <p>', () => {
    const list = document.createElement('ul')
    const item = document.createElement('li')
    const paragraph = document.createElement('p')
    paragraph.textContent = 'пункт'
    item.appendChild(paragraph)
    list.appendChild(item)
    document.body.appendChild(list)
    expect(resolveBlockReorderHandleEl(paragraph)).toBe(item)
    expect(resolveBlockReorderHandleEl(item)).toBe(item)
    list.remove()
  })

  it('считает текст внутри ячейки целью таблицы и не стартует drag с ячейки', () => {
    const table = document.createElement('table')
    const tr = document.createElement('tr')
    const td = document.createElement('td')
    const text = document.createTextNode('ячейка')
    td.appendChild(text)
    tr.appendChild(td)
    table.appendChild(tr)
    document.body.appendChild(table)
    expect(isTableReorderTarget(text)).toBe(true)
    expect(isBlockReorderExemptTarget(text)).toBe(true)
    table.remove()
  })
})
