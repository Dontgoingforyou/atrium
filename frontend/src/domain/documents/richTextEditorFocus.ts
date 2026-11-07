/** Не уводить каретку в конец, если уже правим; при входе в правку фокус обязателен. */
export function shouldMoveRichTextFocusToEnd(params: {
  editable: boolean
  autoFocus: boolean
  editorAlreadyFocused: boolean
  enteringEdit?: boolean
}): boolean {
  if (!params.editable || !params.autoFocus) return false
  if (params.enteringEdit) return true
  return !params.editorAlreadyFocused
}

export type RichTextFocusTarget = { type: 'none' } | { type: 'end' } | { type: 'pos'; pos: number }

/** Каретка при фокусе: точка клика, иначе конец; native в toggle — не уводить в конец. */
export function resolveRichTextFocusTarget(params: {
  editable: boolean
  autoFocus: boolean
  editorAlreadyFocused: boolean
  enteringEdit: boolean
  clickMappedPos: number | null
  docSize: number
  nativeCaretInToggleBody: boolean
}): RichTextFocusTarget {
  if (!params.editable || !params.autoFocus) return { type: 'none' }
  if (params.enteringEdit) {
    const caret = resolveRichTextEnterEditCaret({
      clickMappedPos: params.clickMappedPos,
      docSize: params.docSize,
    })
    if (caret !== 'end') return { type: 'pos', pos: caret }
    if (params.nativeCaretInToggleBody) return { type: 'none' }
    return { type: 'end' }
  }
  if (params.nativeCaretInToggleBody) return { type: 'none' }
  if (params.editorAlreadyFocused) return { type: 'none' }
  return { type: 'end' }
}

/** Клик по документу: каретка в точку клика, иначе в конец (пустой лист / мимо текста). */
export function resolveRichTextEnterEditCaret(params: {
  clickMappedPos: number | null
  docSize: number
}): number | 'end' {
  const pos = params.clickMappedPos
  if (pos == null || pos < 1 || pos > params.docSize) return 'end'
  return pos
}

export function mapClickCoordsToDocPos(
  posAtCoords: (coords: { left: number; top: number }) => { pos: number } | null,
  point: { x: number; y: number },
): number | null {
  return posAtCoords({ left: point.x, top: point.y })?.pos ?? null
}
