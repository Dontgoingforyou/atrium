// @vitest-environment jsdom

import { describe, expect, it } from 'vitest'

import {
  applyBuildinToggleEditChrome,
  buildinToggleAttrsOnTitleEnter,
  emptyParagraphAfterToggleRange,
  insertPlainTextAtSelection,
  invertBuildinToggleOpen,
  isBuildinToggleArrowTarget,
  isCaretInsideNode,
  normalizeBuildinToggleTitle,
  resolveBuildinToggleBodyCaretPos,
  normalizeBuildinToggleTitleLive,
  parseBuildinToggleTitleFromParts,
  shouldApplyRemoteToggleTitle,
  shouldPreventDefaultOnToggleTitleClick,
  shouldPreventDefaultOnToggleTitleKey,
  shouldToggleBuildinOpenOnChromeClick,
} from '@/domain/documents/buildinToggleTitle'

describe('normalizeBuildinToggleTitle', () => {
  it('обрезает пробелы и nbsp', () => {
    expect(normalizeBuildinToggleTitle('  ЧТО\u00a0')).toBe('ЧТО')
  })

  it('пустая строка остаётся пустой', () => {
    expect(normalizeBuildinToggleTitle('   ')).toBe('')
  })
})

describe('normalizeBuildinToggleTitleLive', () => {
  it('не trim во время набора, чтобы не схлопывать пробел', () => {
    expect(normalizeBuildinToggleTitleLive('Hello ')).toBe('Hello ')
    expect(normalizeBuildinToggleTitleLive('  ЧТО')).toBe('  ЧТО')
  })

  it('заменяет nbsp на пробел', () => {
    expect(normalizeBuildinToggleTitleLive('ЧТО\u00a0')).toBe('ЧТО ')
  })
})

describe('shouldPreventDefaultOnToggleTitleClick', () => {
  it('не preventDefault на поле заголовка — иначе Safari/тачпад ломают каретку', () => {
    expect(shouldPreventDefaultOnToggleTitleClick()).toBe(false)
  })
})

describe('клик по chrome toggle: свернуть только стрелкой', () => {
  it('стрелка и край summary тоглят, поле и крестик — нет', () => {
    const header = document.createElement('div')
    header.className = 'buildin-toggle-header'
    const arrow = document.createElement('button')
    arrow.className = 'buildin-toggle-arrow'
    const input = document.createElement('input')
    input.className = 'buildin-toggle-title-input'
    const del = document.createElement('button')
    del.className = 'buildin-toggle-delete'
    header.append(arrow, input, del)

    expect(isBuildinToggleArrowTarget(arrow)).toBe(true)
    expect(shouldToggleBuildinOpenOnChromeClick(arrow)).toBe(true)
    expect(shouldToggleBuildinOpenOnChromeClick(header)).toBe(true)
    expect(shouldToggleBuildinOpenOnChromeClick(input)).toBe(false)
    expect(shouldToggleBuildinOpenOnChromeClick(del)).toBe(false)
    expect(shouldToggleBuildinOpenOnChromeClick(null)).toBe(false)
  })

  it('инвертирует attrs.open, не DOM details.open', () => {
    expect(invertBuildinToggleOpen(true)).toBe(false)
    expect(invertBuildinToggleOpen(false)).toBe(true)
  })
})

describe('пробел в заголовке toggle', () => {
  it('Space надо глушить — иначе details тоглится и каретка уходит в тело', () => {
    expect(shouldPreventDefaultOnToggleTitleKey(' ')).toBe(true)
    expect(shouldPreventDefaultOnToggleTitleKey('Spacebar')).toBe(true)
    expect(shouldPreventDefaultOnToggleTitleKey('Enter')).toBe(false)
  })

  it('вставляет пробел в середину без схлопывания', () => {
    expect(insertPlainTextAtSelection('тест', 4, 4, ' ')).toEqual({ value: 'тест ', caret: 5 })
    expect(insertPlainTextAtSelection('аб', 1, 1, ' ')).toEqual({ value: 'а б', caret: 2 })
  })
})

describe('Enter из заголовка toggle', () => {
  it('каретка в теле блока, не после закрывающего токена', () => {
    expect(resolveBuildinToggleBodyCaretPos(10, 8)).toBe(12)
    expect(isCaretInsideNode(12, 10, 8)).toBe(true)
    expect(isCaretInsideNode(18, 10, 8)).toBe(false)
  })

  it('раскрывает блок, чтобы строка началась внутри, а не за ним', () => {
    expect(buildinToggleAttrsOnTitleEnter({ title: 'Новый раздел', open: false }, 'ЧТО')).toEqual({
      title: 'ЧТО',
      open: true,
    })
  })

  it('пустой абзац сразу за toggle — вырезать, иначе каретка оказывается за блоком', () => {
    expect(
      emptyParagraphAfterToggleRange({
        togglePos: 0,
        toggleSize: 6,
        nextTypeName: 'paragraph',
        nextNodeSize: 2,
        nextEmpty: true,
      }),
    ).toEqual({ from: 6, to: 8 })
    expect(
      emptyParagraphAfterToggleRange({
        togglePos: 0,
        toggleSize: 6,
        nextTypeName: 'paragraph',
        nextNodeSize: 5,
        nextEmpty: false,
      }),
    ).toBeNull()
  })
})

describe('parseBuildinToggleTitleFromParts', () => {
  it('берёт текст summary', () => {
    expect(
      parseBuildinToggleTitleFromParts({
        summaryVisibleText: 'ЧТО',
        detailsTitleAttr: 'старый',
      }),
    ).toBe('ЧТО')
  })

  it('пустой summary → fallback на title атрибут details', () => {
    expect(
      parseBuildinToggleTitleFromParts({
        summaryVisibleText: '  ',
        detailsTitleAttr: 'ЧТО',
      }),
    ).toBe('ЧТО')
  })

  it('XSS-строка остаётся текстом, не пустеет', () => {
    const raw = '<script>alert(1)</script>'
    expect(
      parseBuildinToggleTitleFromParts({
        summaryVisibleText: raw,
        detailsTitleAttr: null,
      }),
    ).toBe(raw)
  })
})

describe('shouldApplyRemoteToggleTitle', () => {
  it('не затирает input в фокусе', () => {
    expect(
      shouldApplyRemoteToggleTitle({
        inputValue: 'ЧТО',
        attrsTitle: '',
        isInputFocused: true,
        isLocallyDirty: false,
      }),
    ).toBe(false)
  })

  it('не затирает локально грязный input после blur', () => {
    expect(
      shouldApplyRemoteToggleTitle({
        inputValue: 'ЧТО',
        attrsTitle: '',
        isInputFocused: false,
        isLocallyDirty: true,
      }),
    ).toBe(false)
  })

  it('применяет attrs, когда input не в фокусе и не dirty', () => {
    expect(
      shouldApplyRemoteToggleTitle({
        inputValue: 'Новый раздел',
        attrsTitle: 'ЧТО',
        isInputFocused: false,
        isLocallyDirty: false,
      }),
    ).toBe(true)
  })
})

describe('applyBuildinToggleEditChrome', () => {
  it('в просмотре блокирует поле и прячет удаление', () => {
    const titleInput = { readOnly: false, tabIndex: 0 }
    const deleteBtn = { hidden: false, disabled: false }
    const contentDOM = { contentEditable: 'true' }
    applyBuildinToggleEditChrome(titleInput, deleteBtn, false, contentDOM)
    expect(titleInput.readOnly).toBe(true)
    expect(titleInput.tabIndex).toBe(-1)
    expect(deleteBtn.hidden).toBe(true)
    expect(deleteBtn.disabled).toBe(true)
    expect(contentDOM.contentEditable).toBe('false')
  })

  it('в правке возвращает поле и крестик', () => {
    const titleInput = { readOnly: true, tabIndex: -1 }
    const deleteBtn = { hidden: true, disabled: true }
    const contentDOM = { contentEditable: 'false' }
    applyBuildinToggleEditChrome(titleInput, deleteBtn, true, contentDOM)
    expect(titleInput.readOnly).toBe(false)
    expect(titleInput.tabIndex).toBe(0)
    expect(deleteBtn.hidden).toBe(false)
    expect(deleteBtn.disabled).toBe(false)
    expect(contentDOM.contentEditable).toBe('true')
  })
})
