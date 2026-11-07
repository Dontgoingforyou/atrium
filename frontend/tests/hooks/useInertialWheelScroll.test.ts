import { describe, expect, it } from 'vitest'

import {
  applyFriction,
  clampVelocity,
  dampWheelDelta,
  resolveDragBoardWheelDelta,
  resolveHorizontalWheelDelta,
} from '../../src/hooks/useInertialWheelScroll'

describe('resolveHorizontalWheelDelta', () => {
  it('трекпад: горизонтальный deltaX сильнее deltaY -> используем deltaX', () => {
    expect(resolveHorizontalWheelDelta(40, 5, false)).toBe(40)
  })

  it('обычное колесо + Shift: deltaY трактуется как горизонталь', () => {
    expect(resolveHorizontalWheelDelta(0, 30, true)).toBe(30)
  })

  it('вертикальный скролл без Shift и без deltaX -> null (не трогаем канбан)', () => {
    expect(resolveHorizontalWheelDelta(0, 30, false)).toBeNull()
  })

  it('deltaY доминирует над небольшим deltaX без Shift -> null', () => {
    expect(resolveHorizontalWheelDelta(2, 30, false)).toBeNull()
  })
})

describe('resolveDragBoardWheelDelta', () => {
  it('при DnD вертикальный жест тачпада едет вбок', () => {
    expect(resolveDragBoardWheelDelta(0, 30, false)).toBe(30)
    expect(resolveDragBoardWheelDelta(2, 30, false)).toBe(30)
  })

  it('горизонтальный deltaX по-прежнему сильнее', () => {
    expect(resolveDragBoardWheelDelta(40, 5, false)).toBe(40)
  })

  it('без движения — null', () => {
    expect(resolveDragBoardWheelDelta(0, 0, false)).toBeNull()
  })
})

describe('clampVelocity', () => {
  it('ограничивает сверху', () => {
    expect(clampVelocity(500, 28)).toBe(28)
  })

  it('ограничивает снизу (отрицательная скорость)', () => {
    expect(clampVelocity(-500, 28)).toBe(-28)
  })

  it('не трогает значение в допустимом диапазоне', () => {
    expect(clampVelocity(20, 28)).toBe(20)
  })
})

describe('dampWheelDelta', () => {
  it('уменьшает чувствительность колеса', () => {
    expect(dampWheelDelta(100)).toBeCloseTo(60)
  })
})

describe('applyFriction', () => {
  it('уменьшает скорость на коэффициент трения', () => {
    expect(applyFriction(100, 0.9, 0.5)).toBeCloseTo(90)
  })

  it('обнуляет скорость ниже порога остановки (торможение до конца)', () => {
    expect(applyFriction(0.4, 0.9, 0.5)).toBe(0)
  })

  it('за несколько шагов скорость затухает до нуля', () => {
    let v = 28
    let steps = 0
    while (v !== 0 && steps < 1000) {
      v = applyFriction(v, 0.84, 0.5)
      steps += 1
    }
    expect(v).toBe(0)
    expect(steps).toBeGreaterThan(0)
    expect(steps).toBeLessThan(200)
  })
})
