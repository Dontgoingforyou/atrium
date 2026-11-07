import { describe, expect, it } from 'vitest'

import { conversionLevel, conversionLevelColor, CONVERSION_LEVEL_COLORS } from '../../../../src/pages/analytics/bench/conversionLevel'

describe('conversionLevel', () => {
  it('пороги high / medium / low как в эталонном дашборде', () => {
    expect(conversionLevel(3)).toBe('high')
    expect(conversionLevel(5.79)).toBe('high')
    expect(conversionLevel(1.5)).toBe('medium')
    expect(conversionLevel(2.02)).toBe('medium')
    expect(conversionLevel(1.49)).toBe('low')
    expect(conversionLevel(0)).toBe('low')
  })

  it('цвет уровня из палитры портала', () => {
    expect(conversionLevelColor(4)).toBe(CONVERSION_LEVEL_COLORS.high)
    expect(conversionLevelColor(1.7)).toBe(CONVERSION_LEVEL_COLORS.medium)
    expect(conversionLevelColor(0.5)).toBe(CONVERSION_LEVEL_COLORS.low)
  })
})
