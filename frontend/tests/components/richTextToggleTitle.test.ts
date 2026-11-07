// @vitest-environment jsdom

import { Editor } from '@tiptap/core'
import StarterKit from '@tiptap/starter-kit'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { BUILDIN_TOGGLE_BODY_ANIM_MS } from '@/domain/documents/buildinToggle'

import { BuildinToggle } from '@/components/tasks/richText/extensions/tiptapBuildinToggleExtension'

function makeEditor(content: string): Editor {
  return new Editor({
    extensions: [StarterKit.configure({ heading: false }), BuildinToggle],
    content,
  })
}

const TOGGLE_HTML =
  '<details class="buildin-toggle"><summary>ЧТО</summary><div class="buildin-toggle-body"><p>тело</p></div></details>'

describe('BuildinToggle title round-trip', () => {
  let editor: Editor | null = null

  afterEach(() => {
    vi.useRealTimers()
    editor?.destroy()
    editor = null
  })

  it('insertBuildinToggle создаёт раскрытый блок', () => {
    editor = makeEditor('<p></p>')
    editor.commands.insertBuildinToggle()
    const toggle = editor.view.dom.querySelector('.buildin-toggle') as HTMLElement | null
    expect(toggle).not.toBeNull()
    expect(toggle!.dataset.expanded).toBe('true')
    expect(toggleTitle(editor)).toBe('Новый раздел')
  })

  it('mousedown по стрелке сворачивает блок, клик по заголовку — нет', () => {
    editor = makeEditor('<p></p>')
    editor.commands.insertBuildinToggle()
    const toggle = editor.view.dom.querySelector('.buildin-toggle') as HTMLElement | null
    const arrow = editor.view.dom.querySelector('.buildin-toggle-arrow') as HTMLButtonElement | null
    const input = editor.view.dom.querySelector('.buildin-toggle-title-input') as HTMLInputElement | null
    expect(toggle).not.toBeNull()
    expect(arrow).not.toBeNull()
    expect(input).not.toBeNull()
    expect(toggle!.dataset.expanded).toBe('true')
    const slot = toggle!.querySelector('.buildin-toggle-body-slot') as HTMLElement | null
    expect(slot?.dataset.state).toBe('open')
    expect(toggle!.querySelector('.buildin-toggle-body-clip')).not.toBeNull()

    input!.focus()
    input!.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }))
    expect(slot?.dataset.state).toBe('open')
    expect(toggleOpen(editor)).toBe(true)

    vi.useFakeTimers()
    arrow!.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, cancelable: true }))
    expect(slot?.dataset.state).toBe('closed')
    expect(toggle!.dataset.expanded).toBe('false')
    expect(toggleOpen(editor)).toBe(true)

    vi.advanceTimersByTime(BUILDIN_TOGGLE_BODY_ANIM_MS)
    expect(toggleOpen(editor)).toBe(false)

    const arrowAfter = editor.view.dom.querySelector('.buildin-toggle-arrow') as HTMLButtonElement | null
    const slotAfter = editor.view.dom.querySelector('.buildin-toggle-body-slot') as HTMLElement | null
    arrowAfter!.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, cancelable: true }))
    expect(slotAfter?.dataset.state).toBe('open')
    expect(toggleOpen(editor)).toBe(false)
    vi.advanceTimersByTime(BUILDIN_TOGGLE_BODY_ANIM_MS)
    expect(toggleOpen(editor)).toBe(true)
    vi.useRealTimers()
  })

  it('сохраняет заголовок HTML→Editor→HTML и не дублирует title на details', () => {
    editor = makeEditor(TOGGLE_HTML)
    const html = editor.getHTML()
    expect(html).toContain('<summary>ЧТО</summary>')
    expect(html).toContain('тело')
    expect(html).not.toMatch(/<details[^>]*\stitle=/)
  })

  it('берёт заголовок из title атрибута, если summary пустой', () => {
    editor = makeEditor(
      '<details class="buildin-toggle" title="ЧТО"><summary></summary><div class="buildin-toggle-body"><p>x</p></div></details>',
    )
    expect(editor.getHTML()).toContain('<summary>ЧТО</summary>')
  })

  function toggleTitle(ed: Editor): string {
    let title = ''
    ed.state.doc.descendants((node) => {
      if (node.type.name === 'buildinToggle') {
        title = String(node.attrs.title ?? '')
        return false
      }
      return true
    })
    return title
  }

  function toggleOpen(ed: Editor): boolean {
    let open = false
    ed.state.doc.descendants((node) => {
      if (node.type.name === 'buildinToggle') {
        open = Boolean(node.attrs.open)
        return false
      }
      return true
    })
    return open
  }

  it('посимвольный ввод не пишет attrs до blur — иначе collab пересоздаёт поле', () => {
    editor = makeEditor(
      '<details class="buildin-toggle"><summary>Новый раздел</summary><div class="buildin-toggle-body"><p></p></div></details>',
    )
    const input = editor.view.dom.querySelector('.buildin-toggle-title-input') as HTMLInputElement | null
    expect(input).not.toBeNull()
    input!.focus()
    let typed = ''
    for (const ch of 'Hello') {
      typed += ch
      input!.value = typed
      input!.dispatchEvent(new Event('input', { bubbles: true }))
      expect(input!.value).toBe(typed)
    }
    expect(toggleTitle(editor)).toBe('Новый раздел')
    expect(input!.value).toBe('Hello')
    input!.dispatchEvent(new Event('blur', { bubbles: true }))
    expect(toggleTitle(editor)).toBe('Hello')
    expect(input!.value).toBe('Hello')
  })

  it('вне правки клик по стрелке всплывает — вход в документ с одного клика', () => {
    editor = makeEditor(TOGGLE_HTML)
    editor.setEditable(false)
    const arrow = editor.view.dom.querySelector('.buildin-toggle-arrow') as HTMLElement | null
    expect(arrow).not.toBeNull()
    let bubbled = false
    editor.view.dom.addEventListener('click', () => {
      bubbled = true
    })
    arrow!.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }))
    expect(bubbled).toBe(true)
  })

  it('вне правки клик по полоске всплывает — вход в документ с одного клика', () => {
    editor = makeEditor(TOGGLE_HTML)
    editor.setEditable(false)
    const header = editor.view.dom.querySelector('.buildin-toggle-header') as HTMLElement | null
    expect(header).not.toBeNull()
    let bubbled = false
    editor.view.dom.addEventListener('click', () => {
      bubbled = true
    })
    header!.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }))
    expect(bubbled).toBe(true)
  })

  it('пробел остаётся в заголовке и не пишет attrs / не уводит в тело', () => {
    editor = makeEditor(
      '<details class="buildin-toggle"><summary>Новый раздел</summary><div class="buildin-toggle-body"><p></p></div></details>',
    )
    const toggle = editor.view.dom.querySelector('.buildin-toggle') as HTMLElement | null
    const input = editor.view.dom.querySelector('.buildin-toggle-title-input') as HTMLInputElement | null
    expect(toggle).not.toBeNull()
    expect(input).not.toBeNull()
    const wasExpanded = toggle!.dataset.expanded
    input!.focus()
    input!.value = 'тест'
    input!.setSelectionRange(4, 4)
    input!.dispatchEvent(new Event('input', { bubbles: true }))
    const space = new KeyboardEvent('keydown', { key: ' ', bubbles: true, cancelable: true })
    input!.dispatchEvent(space)
    expect(space.defaultPrevented).toBe(true)
    expect(input!.value).toBe('тест ')
    expect(toggleTitle(editor)).toBe('Новый раздел')
    expect(toggle!.dataset.expanded).toBe(wasExpanded)
    expect(editor.getHTML()).not.toMatch(/<p> /)
    input!.dispatchEvent(new Event('blur', { bubbles: true }))
    expect(toggleTitle(editor)).toBe('тест')
  })

  it('клик по полю заголовка не preventDefault', () => {
    editor = makeEditor(TOGGLE_HTML)
    const input = editor.view.dom.querySelector('.buildin-toggle-title-input') as HTMLInputElement | null
    expect(input).not.toBeNull()
    const click = new MouseEvent('click', { bubbles: true, cancelable: true })
    input!.dispatchEvent(click)
    expect(click.defaultPrevented).toBe(false)
  })

  it('Enter из заголовка раскрывает блок и ставит каретку в тело, не после блока', () => {
    editor = makeEditor(
      '<details class="buildin-toggle"><summary>Новый раздел</summary><div class="buildin-toggle-body"><p></p></div></details>',
    )
    const toggle = editor.view.dom.querySelector('.buildin-toggle') as HTMLElement | null
    const input = editor.view.dom.querySelector('.buildin-toggle-title-input') as HTMLInputElement | null
    expect(toggle).not.toBeNull()
    expect(input).not.toBeNull()
    input!.value = 'ЧТО'
    input!.dispatchEvent(new Event('input', { bubbles: true }))
    input!.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true, cancelable: true }))
    expect(toggle!.dataset.expanded).toBe('true')
    expect(toggleTitle(editor)).toBe('ЧТО')
    let togglePos = -1
    let toggleSize = 0
    editor.state.doc.descendants((node, pos) => {
      if (node.type.name === 'buildinToggle') {
        togglePos = pos
        toggleSize = node.nodeSize
        return false
      }
      return true
    })
    const caret = editor.state.selection.from
    expect(caret).toBeGreaterThan(togglePos)
    expect(caret).toBeLessThan(togglePos + toggleSize)
  })

  it('input + Enter оставляет заголовок в attrs и HTML', () => {
    editor = makeEditor(
      '<details class="buildin-toggle"><summary>Новый раздел</summary><div class="buildin-toggle-body"><p></p></div></details>',
    )
    const input = editor.view.dom.querySelector('.buildin-toggle-title-input') as HTMLInputElement | null
    expect(input).not.toBeNull()
    input!.value = 'ЧТО'
    input!.dispatchEvent(new Event('input', { bubbles: true }))
    input!.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }))
    expect(editor.getHTML()).toContain('<summary>ЧТО</summary>')
    let title = ''
    editor.state.doc.descendants((node) => {
      if (node.type.name === 'buildinToggle') {
        title = String(node.attrs.title ?? '')
        return false
      }
      return true
    })
    expect(title).toBe('ЧТО')
  })

  it('XSS-строка в summary остаётся текстом после round-trip', () => {
    editor = makeEditor(
      '<details class="buildin-toggle"><summary>&lt;script&gt;alert(1)&lt;/script&gt;</summary><div class="buildin-toggle-body"><p>x</p></div></details>',
    )
    const html = editor.getHTML()
    expect(html).not.toContain('<script>')
    expect(html).toContain('alert(1)')
  })

  it('вне правки не меняет заголовок и прячет удаление', () => {
    editor = makeEditor(TOGGLE_HTML)
    editor.setEditable(false)
    const input = editor.view.dom.querySelector('.buildin-toggle-title-input') as HTMLInputElement | null
    const del = editor.view.dom.querySelector('.buildin-toggle-delete') as HTMLButtonElement | null
    expect(input?.readOnly).toBe(true)
    expect(del?.hidden).toBe(true)
    input!.value = 'ХАК'
    input!.dispatchEvent(new Event('input', { bubbles: true }))
    expect(editor.getHTML()).toContain('<summary>ЧТО</summary>')
    expect(editor.getHTML()).not.toContain('ХАК')
  })

  it('перестановка top-level toggle сохраняется в HTML', () => {
    editor = makeEditor(
      '<details class="buildin-toggle"><summary>Первый</summary><div class="buildin-toggle-body"><p>a</p></div></details>' +
        '<details class="buildin-toggle"><summary>Второй</summary><div class="buildin-toggle-body"><p>b</p></div></details>',
    )
    const json = editor.getJSON()
    const blocks = json.content ?? []
    const swapped = { ...json, content: [blocks[1], blocks[0]] }
    editor.commands.setContent(swapped)
    const html = editor.getHTML()
    expect(html.indexOf('Второй')).toBeLessThan(html.indexOf('Первый'))
  })
})
