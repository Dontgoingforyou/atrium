import { describe, expect, it } from 'vitest'

import {
  BLOCK_REORDER_DROP_LINE_PX,
  blockReorderDropLineRect,
  blockReorderHandleRailLeft,
  blockReorderHandleRect,
  isPointInBlockReorderHandleApproach,
  isPointInBlockReorderHandleLane,
  shouldHoldBlockReorderHandleWithoutResync,
  shouldKeepBlockReorderHandleVisible,
  eventTargetElement,
  previewListWrapperTagName,
  insertPosForKeyboardMove,
  insertPosForSiblingMove,
  isAtomicReorderBlock,
  isBlockReorderHandleTarget,
  isInsertInsideDraggedBlock,
  isSameBlockDrop,
  mappedInsertPosAfterDelete,
  resolveBlockReorderGestureOrigin,
  shouldShowBlockReorderHandle,
  shouldStartBlockReorder,
  shouldSuppressClickAfterBlockReorder,
  canBeginBlockReorderGesture,
  siblingOverIndexFromY,
  siblingReorderShiftY,
} from '@/domain/documents/richTextBlockReorder'

describe('shouldShowBlockReorderHandle', () => {
  it('скрывает ручку на пустой строке', () => {
    expect(shouldShowBlockReorderHandle({ textLength: 0, isAtomicBlock: false })).toBe(false)
  })

  it('показывает ручку, если в блоке есть хотя бы один символ', () => {
    expect(shouldShowBlockReorderHandle({ textLength: 1, isAtomicBlock: false })).toBe(true)
  })

  it('показывает ручку у атомарного блока без текста', () => {
    expect(shouldShowBlockReorderHandle({ textLength: 0, isAtomicBlock: true })).toBe(true)
  })
})

describe('isAtomicReorderBlock', () => {
  it('считает таблицу, картинку и раздел атомарными', () => {
    expect(isAtomicReorderBlock('table')).toBe(true)
    expect(isAtomicReorderBlock('documentImage')).toBe(true)
    expect(isAtomicReorderBlock('buildinToggle')).toBe(true)
    expect(isAtomicReorderBlock('paragraph')).toBe(false)
  })
})

describe('shouldStartBlockReorder', () => {
  it('не стартует, пока сдвиг меньше порога', () => {
    expect(shouldStartBlockReorder(0, 4)).toBe(false)
  })

  it('стартует при вертикальном жесте', () => {
    expect(shouldStartBlockReorder(2, 12)).toBe(true)
  })

  it('не стартует при горизонтальном выделении текста', () => {
    expect(shouldStartBlockReorder(20, 4)).toBe(false)
  })

  it('джиттер тачпада с текста заголовка не стартует reorder', () => {
    expect(shouldStartBlockReorder(1, 10, { origin: 'text' })).toBe(false)
    expect(shouldStartBlockReorder(0, 8, { origin: 'text' })).toBe(false)
  })

  it('явный вертикальный жест с ручки стартует reorder', () => {
    expect(shouldStartBlockReorder(2, 12, { origin: 'handle' })).toBe(true)
  })

  it('с шапки toggle стартует только после большего вертикального сдвига', () => {
    expect(shouldStartBlockReorder(2, 12, { origin: 'toggle-header' })).toBe(false)
    expect(shouldStartBlockReorder(2, 20, { origin: 'toggle-header' })).toBe(true)
    expect(shouldStartBlockReorder(20, 4, { origin: 'toggle-header' })).toBe(false)
  })
})

describe('canBeginBlockReorderGesture', () => {
  it('с текста тела жест не начинается, с ручки и шапки toggle — да', () => {
    expect(canBeginBlockReorderGesture('text')).toBe(false)
    expect(canBeginBlockReorderGesture('handle')).toBe(true)
    expect(canBeginBlockReorderGesture('toggle-header')).toBe(true)
  })
})

describe('resolveBlockReorderGestureOrigin', () => {
  it('ручка важнее шапки, шапка важнее текста', () => {
    expect(resolveBlockReorderGestureOrigin(true, true)).toBe('handle')
    expect(resolveBlockReorderGestureOrigin(false, true)).toBe('toggle-header')
    expect(resolveBlockReorderGestureOrigin(false, false)).toBe('text')
  })
})

describe('shouldSuppressClickAfterBlockReorder', () => {
  it('глушит click после активного drag (тачпад шлёт лишний click)', () => {
    expect(shouldSuppressClickAfterBlockReorder(true)).toBe(true)
    expect(shouldSuppressClickAfterBlockReorder(false)).toBe(false)
  })
})

describe('mappedInsertPosAfterDelete', () => {
  it('сдвигает insert, если блок удалили выше точки вставки', () => {
    expect(mappedInsertPosAfterDelete(20, 0, 10)).toBe(10)
  })

  it('не сдвигает, если блок ниже точки вставки', () => {
    expect(mappedInsertPosAfterDelete(5, 10, 8)).toBe(5)
  })
})

describe('isSameBlockDrop', () => {
  it('no-op, если бросили на то же место', () => {
    expect(isSameBlockDrop(0, 0, 10)).toBe(true)
    expect(isSameBlockDrop(10, 0, 10)).toBe(true)
    expect(isSameBlockDrop(20, 0, 10)).toBe(false)
  })
})

describe('isInsertInsideDraggedBlock', () => {
  it('не даёт вставить блок внутрь самого себя', () => {
    expect(isInsertInsideDraggedBlock(5, 0, 10)).toBe(true)
    expect(isInsertInsideDraggedBlock(0, 0, 10)).toBe(false)
    expect(isInsertInsideDraggedBlock(10, 0, 10)).toBe(false)
  })
})

describe('siblingReorderShiftY', () => {
  it('сдвигает промежуточные блоки вверх при переносе вниз', () => {
    expect(siblingReorderShiftY(0, 1, 3, 40)).toBe(0)
    expect(siblingReorderShiftY(1, 1, 3, 40)).toBe(0)
    expect(siblingReorderShiftY(2, 1, 3, 40)).toBe(-40)
    expect(siblingReorderShiftY(3, 1, 3, 40)).toBe(-40)
  })

  it('сдвигает промежуточные блоки вниз при переносе вверх', () => {
    expect(siblingReorderShiftY(0, 3, 1, 40)).toBe(0)
    expect(siblingReorderShiftY(1, 3, 1, 40)).toBe(40)
    expect(siblingReorderShiftY(2, 3, 1, 40)).toBe(40)
    expect(siblingReorderShiftY(3, 3, 1, 40)).toBe(0)
  })
})

describe('siblingOverIndexFromY', () => {
  it('берёт ближайшую середину блока', () => {
    expect(siblingOverIndexFromY(25, [10, 50, 90])).toBe(0)
    expect(siblingOverIndexFromY(48, [10, 50, 90])).toBe(1)
    expect(siblingOverIndexFromY(200, [10, 50, 90])).toBe(2)
  })
})

describe('insertPosForSiblingMove', () => {
  const ranges = [
    { from: 0, size: 3 },
    { from: 3, size: 3 },
    { from: 6, size: 5 },
  ]

  it('вставляет после цели, если блок уезжает вниз', () => {
    expect(insertPosForSiblingMove(ranges, 0, 2)).toBe(11)
  })

  it('вставляет перед целью, если блок уезжает вверх', () => {
    expect(insertPosForSiblingMove(ranges, 2, 0)).toBe(0)
  })

  it('оставляет позицию источника, если слот не менялся', () => {
    expect(insertPosForSiblingMove(ranges, 1, 1)).toBe(3)
  })
})

describe('blockReorderDropLineRect', () => {
  const rel = [
    { top: 0, left: 8, height: 20, width: 100 },
    { top: 24, left: 8, height: 30, width: 120 },
    { top: 60, left: 8, height: 16, width: 80 },
  ]

  it('ставит линию по верху цели при переносе вверх', () => {
    expect(blockReorderDropLineRect(2, 0, rel)).toEqual({
      top: 0,
      left: 8,
      width: 100,
      height: BLOCK_REORDER_DROP_LINE_PX,
    })
  })

  it('ставит линию по низу цели при переносе вниз', () => {
    expect(blockReorderDropLineRect(0, 2, rel)).toEqual({
      top: 76 - BLOCK_REORDER_DROP_LINE_PX,
      left: 8,
      width: 80,
      height: BLOCK_REORDER_DROP_LINE_PX,
    })
  })

  it('скрывает линию, если слот не менялся', () => {
    expect(blockReorderDropLineRect(1, 1, rel)).toBeNull()
  })

  it('скрывает линию при пустом или битом индексе', () => {
    expect(blockReorderDropLineRect(0, 0, [])).toBeNull()
    expect(blockReorderDropLineRect(0, -1, rel)).toBeNull()
    expect(blockReorderDropLineRect(0, 9, rel)).toBeNull()
  })
})

describe('blockReorderHandleRect', () => {
  it('ставит ручку слева от верхней кромки блока', () => {
    expect(blockReorderHandleRect({ top: 40, left: 24 }, { width: 16, height: 20 })).toEqual({
      left: 8,
      top: 40,
    })
  })

  it('при заданном жёлобе не едет за отступом блока', () => {
    expect(blockReorderHandleRect({ top: 40, left: 80 }, { width: 16, height: 20 }, 20)).toEqual({
      left: 20,
      top: 40,
    })
  })
})

describe('blockReorderHandleRailLeft', () => {
  it('ставит рельс слева от колонки текста на ширину ручки', () => {
    expect(blockReorderHandleRailLeft(100, 16)).toBe(84)
  })
})

describe('shouldKeepBlockReorderHandleVisible', () => {
  const handleRect = { left: 84, top: 40, width: 16, height: 20 }
  const editorLeft = 100

  it('держит ручку над редактором или над самой ручкой', () => {
    expect(
      shouldKeepBlockReorderHandleVisible({
        overEditor: true,
        overHandle: false,
        handleVisible: false,
        clientX: 0,
        clientY: 0,
        handleRect: null,
        editorLeft,
      }),
    ).toBe(true)
    expect(
      shouldKeepBlockReorderHandleVisible({
        overEditor: false,
        overHandle: true,
        handleVisible: true,
        clientX: 90,
        clientY: 50,
        handleRect,
        editorLeft,
      }),
    ).toBe(true)
  })

  it('держит ручку в зазоре между блоком и рельсом', () => {
    expect(isPointInBlockReorderHandleApproach(90, 50, handleRect, editorLeft)).toBe(true)
    expect(
      shouldKeepBlockReorderHandleVisible({
        overEditor: false,
        overHandle: false,
        handleVisible: true,
        clientX: 90,
        clientY: 50,
        handleRect,
        editorLeft,
      }),
    ).toBe(true)
  })

  it('прячет, если курсор далеко или ручка уже скрыта', () => {
    expect(
      shouldKeepBlockReorderHandleVisible({
        overEditor: false,
        overHandle: false,
        handleVisible: true,
        clientX: 10,
        clientY: 200,
        handleRect,
        editorLeft,
      }),
    ).toBe(false)
    expect(
      shouldKeepBlockReorderHandleVisible({
        overEditor: false,
        overHandle: false,
        handleVisible: false,
        clientX: 90,
        clientY: 50,
        handleRect,
        editorLeft,
      }),
    ).toBe(false)
  })
})

describe('shouldHoldBlockReorderHandleWithoutResync', () => {
  const handleRect = { left: 84, top: 40, width: 16, height: 20 }
  const blockRect = { left: 100, top: 40, height: 120 }
  const editorLeft = 100

  it('держит якорь в левой полосе карточки, даже если posAtCoords ушёл в соседний абзац', () => {
    expect(isPointInBlockReorderHandleLane(96, 80, handleRect, blockRect, editorLeft)).toBe(true)
    expect(
      shouldHoldBlockReorderHandleWithoutResync({
        overHandle: false,
        handleVisible: true,
        isAtomicBlock: true,
        clientX: 96,
        clientY: 80,
        handleRect,
        blockRect,
        editorLeft,
      }),
    ).toBe(true)
  })

  it('не держит обычный абзац — у него posAtCoords слева не срывается', () => {
    expect(
      shouldHoldBlockReorderHandleWithoutResync({
        overHandle: false,
        handleVisible: true,
        isAtomicBlock: false,
        clientX: 96,
        clientY: 80,
        handleRect,
        blockRect,
        editorLeft,
      }),
    ).toBe(false)
  })

  it('не держит, если курсор уже над другим блоком правее карточки', () => {
    expect(
      shouldHoldBlockReorderHandleWithoutResync({
        overHandle: false,
        handleVisible: true,
        isAtomicBlock: true,
        clientX: 180,
        clientY: 20,
        handleRect,
        blockRect,
        editorLeft,
      }),
    ).toBe(false)
  })
})

describe('previewListWrapperTagName', () => {
  it('для пункта нумерованного списка оборачивает в ol', () => {
    expect(previewListWrapperTagName('OL')).toBe('OL')
  })

  it('для маркера и чеклиста оборачивает в ul', () => {
    expect(previewListWrapperTagName('UL')).toBe('UL')
    expect(previewListWrapperTagName(null)).toBe('UL')
  })
})

describe('eventTargetElement', () => {
  it('пустой target даёт null', () => {
    expect(eventTargetElement(null)).toBeNull()
  })
})

describe('isBlockReorderHandleTarget', () => {
  it('не считает целью пустой указатель', () => {
    expect(isBlockReorderHandleTarget(null)).toBe(false)
  })
})

describe('insertPosForKeyboardMove', () => {
  const ranges = [
    { from: 0, size: 3 },
    { from: 3, size: 3 },
    { from: 6, size: 5 },
  ]

  it('сдвигает блок на одного соседа вниз', () => {
    expect(insertPosForKeyboardMove(ranges, 0, 'down')).toBe(6)
  })

  it('сдвигает блок на одного соседа вверх', () => {
    expect(insertPosForKeyboardMove(ranges, 6, 'up')).toBe(3)
  })

  it('не двигает крайние блоки за пределы списка', () => {
    expect(insertPosForKeyboardMove(ranges, 0, 'up')).toBeNull()
    expect(insertPosForKeyboardMove(ranges, 6, 'down')).toBeNull()
  })
})
