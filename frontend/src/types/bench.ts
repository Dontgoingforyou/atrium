export type BenchDashboardFilters = {
  year?: number
  specializations?: string[]
  month?: number
  dateFrom?: string
  dateTo?: string
}

export type BenchCards = {
  avg_rate: number | null
  avg_time_to_hire_days: number | null
  offers: number
  offer_conversion: number
  project_starts: number
  cv_sent: number
  rejections: number
}

export type BenchFunnel = {
  cv_sent: number
  screening: number
  internal_interview: number
  tech_stage_1: number
  final_stage: number
  offers: number
  project_starts: number
}

export type BenchSpecializationRow = {
  specialization: string
  avg_rate: number | null
  cv_sent: number
  offers: number
  project_starts: number
  rejections: number
  offer_conversion: number
  project_conversion: number
}

export type BenchMonthlyPoint = {
  label: string
  year: number
  month: string
  month_num: number
  cv_sent: number
  offers: number
  project_starts: number
}

export type BenchConversionBySpec = {
  specialization: string
  offer_conversion: number
  project_conversion: number
}

export type BenchYearCounts = {
  offers: number
  starts: number
}

export type BenchMonthlySummary = {
  years: number[]
  rows: {
    month: string
    month_num: number
    by_year: Record<string, BenchYearCounts>
  }[]
  totals: Record<string, BenchYearCounts>
}

export type BenchDashboard = {
  cards: BenchCards
  funnel: BenchFunnel
  specialization_stats: BenchSpecializationRow[]
  monthly_dynamics: BenchMonthlyPoint[]
  conversion_by_spec: BenchConversionBySpec[]
  monthly_summary: BenchMonthlySummary
  years: number[]
  specializations: string[]
  last_success_at: string | null
  is_stale: boolean
  stale_message: string | null
}

export const BENCH_MONTH_OPTIONS = [
  { value: 1, label: 'Январь' },
  { value: 2, label: 'Февраль' },
  { value: 3, label: 'Март' },
  { value: 4, label: 'Апрель' },
  { value: 5, label: 'Май' },
  { value: 6, label: 'Июнь' },
  { value: 7, label: 'Июль' },
  { value: 8, label: 'Август' },
  { value: 9, label: 'Сентябрь' },
  { value: 10, label: 'Октябрь' },
  { value: 11, label: 'Ноябрь' },
  { value: 12, label: 'Декабрь' },
] as const
