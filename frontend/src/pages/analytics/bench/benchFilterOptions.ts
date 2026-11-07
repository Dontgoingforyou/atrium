import type { SearchablePickerOption } from '../../../components/common/searchablePickerUtils'

export const BENCH_FILTER_SPECIALIZATION_LABEL = 'Специализация'
export const BENCH_FILTER_PERIOD_LABEL = 'Период'

export function benchSpecializationPickerOptions(
  specializations: readonly string[],
): SearchablePickerOption[] {
  return specializations.map((spec) => ({ value: spec, label: spec }))
}

export function formatBenchPeriodLabels(dateFrom: string, dateTo: string): string[] {
  if (!dateFrom && !dateTo) return []
  if (dateFrom && dateTo) return [`${dateFrom} — ${dateTo}`]
  return [dateFrom || dateTo]
}
