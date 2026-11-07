import { describe, expect, it } from 'vitest'

import {
  caretPosInFirstToggleBodyBlock,
  findBuildinToggleDepth,
  resolveInsertedBuildinTogglePos,
  shouldApplyNativeSelectionFromPm,
  shouldFollowPmCaretAfterKey,
  shouldInterceptToggleBodyEnter,
  shouldProtectBuildinToggleFromKeyboardDelete,
  shouldSyncPmSelectionFromNative,
  shouldSyncToggleSelectionOnKey,
  toggleBodyContentEditable,
} from '@/domain/documents/buildinToggleSelection'

function fakeFrom(ancestors: string[]) {
  const names = ['doc', ...ancestors]
  return {
    depth: names.length - 1,
    node: (depth: number) => ({ type: { name: names[depth] ?? 'unknown' } }),
  }
}

describe('shouldSyncPmSelectionFromNative', () => {
  const toggle = { togglePos: 10, toggleSize: 20 }

  it('синхронизирует, если native-каретка в теле, а PM — в другом месте', () => {
    expect(
      shouldSyncPmSelectionFromNative({
        nativeInsideContentDom: true,
        mappedFrom: 14,
        mappedTo: 14,
        ...toggle,
        pmFrom: 80,
        pmTo: 80,
      }),
    ).toBe(true)
  })

  it('синхронизирует native-range как range, а не как точку', () => {
    expect(
      shouldSyncPmSelectionFromNative({
        nativeInsideContentDom: true,
        mappedFrom: 14,
        mappedTo: 18,
        ...toggle,
        pmFrom: 80,
        pmTo: 80,
      }),
    ).toBe(true)
  })

  it('не трогает, если PM уже на том же месте', () => {
    expect(
      shouldSyncPmSelectionFromNative({
        nativeInsideContentDom: true,
        mappedFrom: 14,
        mappedTo: 14,
        ...toggle,
        pmFrom: 14,
        pmTo: 14,
      }),
    ).toBe(false)
  })

  it('не схлопывает, если PM уже совпадает с native-range', () => {
    expect(
      shouldSyncPmSelectionFromNative({
        nativeInsideContentDom: true,
        mappedFrom: 14,
        mappedTo: 18,
        ...toggle,
        pmFrom: 14,
        pmTo: 18,
      }),
    ).toBe(false)
  })

  it('не уводит каретку, если native вне тела или pos вне toggle', () => {
    expect(
      shouldSyncPmSelectionFromNative({
        nativeInsideContentDom: false,
        mappedFrom: 14,
        mappedTo: 14,
        ...toggle,
        pmFrom: 80,
        pmTo: 80,
      }),
    ).toBe(false)
    expect(
      shouldSyncPmSelectionFromNative({
        nativeInsideContentDom: true,
        mappedFrom: null,
        mappedTo: null,
        ...toggle,
        pmFrom: 80,
        pmTo: 80,
      }),
    ).toBe(false)
    expect(
      shouldSyncPmSelectionFromNative({
        nativeInsideContentDom: true,
        mappedFrom: 80,
        mappedTo: 80,
        ...toggle,
        pmFrom: 80,
        pmTo: 80,
      }),
    ).toBe(false)
    expect(
      shouldSyncPmSelectionFromNative({
        nativeInsideContentDom: true,
        mappedFrom: 14,
        mappedTo: 80,
        ...toggle,
        pmFrom: 80,
        pmTo: 80,
      }),
    ).toBe(false)
  })
})

describe('toggleBodyContentEditable', () => {
  it('тело блока редактируется только в режиме правки', () => {
    expect(toggleBodyContentEditable(true)).toBe('true')
    expect(toggleBodyContentEditable(false)).toBe('false')
  })
})

describe('shouldSyncToggleSelectionOnKey', () => {
  it('синхронизирует перед переносом строки и удалением', () => {
    expect(shouldSyncToggleSelectionOnKey('Enter')).toBe(true)
    expect(shouldSyncToggleSelectionOnKey('Backspace')).toBe(true)
    expect(shouldSyncToggleSelectionOnKey('Delete')).toBe(true)
    expect(shouldSyncToggleSelectionOnKey('ArrowLeft')).toBe(true)
    expect(shouldSyncToggleSelectionOnKey('a')).toBe(false)
  })
})

describe('findBuildinToggleDepth', () => {
  it('находит toggle среди предков, иначе null', () => {
    expect(findBuildinToggleDepth(fakeFrom(['buildinToggle', 'paragraph']))).toBe(1)
    expect(findBuildinToggleDepth(fakeFrom(['paragraph']))).toBe(null)
  })
})

describe('shouldProtectBuildinToggleFromKeyboardDelete', () => {
  function $fromAtToggleStart() {
    return {
      depth: 2,
      parentOffset: 0,
      node: (depth: number) => ({
        type: { name: depth === 1 ? 'buildinToggle' : depth === 2 ? 'paragraph' : 'doc' },
      }),
      before: (depth: number) => (depth === 1 ? 10 : 11),
    }
  }

  it('защищает начало первого блока toggle', () => {
    expect(
      shouldProtectBuildinToggleFromKeyboardDelete({ empty: true, $from: $fromAtToggleStart() }),
    ).toBe(true)
  })

  it('не защищает непустое выделение и каретку вне toggle', () => {
    expect(
      shouldProtectBuildinToggleFromKeyboardDelete({ empty: false, $from: $fromAtToggleStart() }),
    ).toBe(false)
    expect(
      shouldProtectBuildinToggleFromKeyboardDelete({
        empty: true,
        $from: {
          depth: 1,
          parentOffset: 0,
          node: (depth: number) => ({ type: { name: depth === 1 ? 'paragraph' : 'doc' } }),
          before: () => 0,
        },
      }),
    ).toBe(false)
  })
})

describe('caretPosInFirstToggleBodyBlock / resolveInsertedBuildinTogglePos', () => {
  it('каретка — сразу внутри первого абзаца тела', () => {
    expect(caretPosInFirstToggleBodyBlock(10)).toBe(12)
  })

  it('берёт NodeSelection, позицию внутри или узел перед кареткой', () => {
    const inside = {
      depth: 2,
      pos: 14,
      node: (depth: number) => ({
        type: { name: depth === 1 ? 'buildinToggle' : depth === 2 ? 'paragraph' : 'doc' },
      }),
      before: (depth: number) => (depth === 1 ? 10 : 11),
      nodeBefore: null,
    }
    expect(
      resolveInsertedBuildinTogglePos({
        $from: inside,
        selectedNodeName: null,
        selectedNodePos: null,
      }),
    ).toBe(10)
    expect(
      resolveInsertedBuildinTogglePos({
        $from: {
          depth: 1,
          pos: 24,
          node: () => ({ type: { name: 'doc' } }),
          before: () => 0,
          nodeBefore: { type: { name: 'buildinToggle' }, nodeSize: 8 },
        },
        selectedNodeName: null,
        selectedNodePos: null,
      }),
    ).toBe(16)
    expect(
      resolveInsertedBuildinTogglePos({
        $from: {
          depth: 0,
          pos: 10,
          node: () => ({ type: { name: 'doc' } }),
          before: () => 0,
          nodeBefore: null,
        },
        selectedNodeName: 'buildinToggle',
        selectedNodePos: 4,
      }),
    ).toBe(4)
  })
})

describe('shouldFollowPmCaretAfterKey', () => {
  it('после Enter native-каретка должна догнать PM', () => {
    expect(shouldFollowPmCaretAfterKey('Enter')).toBe(true)
    expect(shouldFollowPmCaretAfterKey('Backspace')).toBe(false)
  })
})

describe('shouldInterceptToggleBodyEnter', () => {
  it('обычный Enter перехватывает, модификаторы и IME — нет', () => {
    expect(
      shouldInterceptToggleBodyEnter({
        shiftKey: false,
        ctrlKey: false,
        metaKey: false,
        altKey: false,
        isComposing: false,
      }),
    ).toBe(true)
    expect(
      shouldInterceptToggleBodyEnter({
        shiftKey: true,
        ctrlKey: false,
        metaKey: false,
        altKey: false,
        isComposing: false,
      }),
    ).toBe(false)
    expect(
      shouldInterceptToggleBodyEnter({
        shiftKey: false,
        ctrlKey: false,
        metaKey: false,
        altKey: false,
        isComposing: true,
      }),
    ).toBe(false)
  })
})

describe('shouldApplyNativeSelectionFromPm', () => {
  it('ставит DOM-каретку, если PM в toggle, а native ещё на старой строке', () => {
    expect(
      shouldApplyNativeSelectionFromPm({
        pmInsideToggle: true,
        nativeMappedPos: 14,
        pmFrom: 18,
      }),
    ).toBe(true)
    expect(
      shouldApplyNativeSelectionFromPm({
        pmInsideToggle: true,
        nativeMappedPos: 18,
        pmFrom: 18,
      }),
    ).toBe(false)
    expect(
      shouldApplyNativeSelectionFromPm({
        pmInsideToggle: false,
        nativeMappedPos: 14,
        pmFrom: 18,
      }),
    ).toBe(false)
  })
})
