import { describe, expect, it } from 'vitest'

import {
  BENCH_FILTER_PERIOD_LABEL,
  BENCH_FILTER_SPECIALIZATION_LABEL,
  benchSpecializationPickerOptions,
  formatBenchPeriodLabels,
} from '../../../../src/pages/analytics/bench/benchFilterOptions'

describe('benchFilterOptions', () => {
  it('каталог специализаций без пункта Все — пустой выбор значит все', () => {
    const options = benchSpecializationPickerOptions(['Android', 'iOS'])
    expect(options.map((opt) => opt.value)).toEqual(['Android', 'iOS'])
    expect(options.some((opt) => opt.value === 'iOS')).toBe(true)
  })

  it('подписи периода пустые без дат', () => {
    expect(formatBenchPeriodLabels('', '')).toEqual([])
    expect(formatBenchPeriodLabels('2026-01-01', '2026-01-31')).toEqual(['2026-01-01 — 2026-01-31'])
  })

  it('лейблы полей без Год и Месяц', () => {
    expect(BENCH_FILTER_SPECIALIZATION_LABEL).toBe('Специализация')
    expect(BENCH_FILTER_PERIOD_LABEL).toBe('Период')
  })
})
