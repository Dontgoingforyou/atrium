import { describe, expect, it } from 'vitest'

import {
  mapClickCoordsToDocPos,
  resolveRichTextEnterEditCaret,
  resolveRichTextFocusTarget,
  shouldMoveRichTextFocusToEnd,
} from '@/domain/documents/richTextEditorFocus'

describe('shouldMoveRichTextFocusToEnd', () => {
  it('не уводит каретку в конец, если уже правим и редактор в фокусе', () => {
    expect(
      shouldMoveRichTextFocusToEnd({
        editable: true,
        autoFocus: true,
        editorAlreadyFocused: true,
        enteringEdit: false,
      }),
    ).toBe(false)
  })

  it('ставит фокус при входе в правку, даже если клик уже сфокусировал поле', () => {
    expect(
      shouldMoveRichTextFocusToEnd({
        editable: true,
        autoFocus: true,
        editorAlreadyFocused: true,
        enteringEdit: true,
      }),
    ).toBe(true)
  })

  it('ставит фокус в конец при входе в правку', () => {
    expect(
      shouldMoveRichTextFocusToEnd({
        editable: true,
        autoFocus: true,
        editorAlreadyFocused: false,
        enteringEdit: true,
      }),
    ).toBe(true)
  })

  it('не двигает фокус вне правки', () => {
    expect(
      shouldMoveRichTextFocusToEnd({
        editable: false,
        autoFocus: true,
        editorAlreadyFocused: false,
      }),
    ).toBe(false)
  })

})

describe('resolveRichTextEnterEditCaret', () => {
  it('ставит каретку в точку клика, иначе в конец документа', () => {
    expect(resolveRichTextEnterEditCaret({ clickMappedPos: 14, docSize: 80 })).toBe(14)
    expect(resolveRichTextEnterEditCaret({ clickMappedPos: null, docSize: 80 })).toBe('end')
    expect(resolveRichTextEnterEditCaret({ clickMappedPos: 0, docSize: 80 })).toBe('end')
    expect(resolveRichTextEnterEditCaret({ clickMappedPos: 81, docSize: 80 })).toBe('end')
  })
})

describe('mapClickCoordsToDocPos', () => {
  it('берёт pos из posAtCoords или null', () => {
    expect(mapClickCoordsToDocPos(() => ({ pos: 14 }), { x: 10, y: 20 })).toBe(14)
    expect(mapClickCoordsToDocPos(() => null, { x: 10, y: 20 })).toBe(null)
  })
})

describe('resolveRichTextFocusTarget', () => {
  const base = {
    editable: true,
    autoFocus: true,
    editorAlreadyFocused: false,
    clickMappedPos: null as number | null,
    docSize: 80,
    nativeCaretInToggleBody: false,
  }

  it('при входе в правку ставит каретку в точку клика', () => {
    expect(
      resolveRichTextFocusTarget({
        ...base,
        enteringEdit: true,
        clickMappedPos: 14,
      }),
    ).toEqual({ type: 'pos', pos: 14 })
  })

  it('не уводит в конец, если native-каретка уже в теле toggle', () => {
    expect(
      resolveRichTextFocusTarget({
        ...base,
        enteringEdit: true,
        editorAlreadyFocused: true,
        nativeCaretInToggleBody: true,
      }),
    ).toEqual({ type: 'none' })
  })

  it('без клика и без native в toggle — в конец документа', () => {
    expect(resolveRichTextFocusTarget({ ...base, enteringEdit: true })).toEqual({ type: 'end' })
  })
})
