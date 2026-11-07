import { useMutation, useQuery } from '@tanstack/react-query'
import { useState } from 'react'

import { exportBenchDashboard, fetchBenchDashboard } from '../../../api/bench/benchApi'
import { benchDashboardQueryKey } from '../../../api/bench/benchQueryKeys'
import { useNotifyToast } from '../../../hooks/useNotifyToast'
import { userFacingMessageFromUnknown } from '../../../utils/apiUserMessage'
import type { BenchDashboardFilters } from '../../../types/bench'

export function useAnalyticsBenchPageController() {
  const notify = useNotifyToast()
  const [specializations, setSpecializations] = useState<string[]>([])
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')

  const filters: BenchDashboardFilters = {
    specializations: specializations.length ? specializations : undefined,
    dateFrom: dateFrom || undefined,
    dateTo: dateTo || undefined,
  }

  const dashboardQuery = useQuery({
    queryKey: benchDashboardQueryKey(filters),
    queryFn: () => fetchBenchDashboard(filters),
  })

  const exportCsv = useMutation({
    mutationFn: () => exportBenchDashboard(filters, 'csv'),
    onError: (error: unknown) => {
      notify(userFacingMessageFromUnknown(error))
    },
  })

  const exportXlsx = useMutation({
    mutationFn: () => exportBenchDashboard(filters, 'xlsx'),
    onError: (error: unknown) => {
      notify(userFacingMessageFromUnknown(error))
    },
  })

  function handlePeriodChange(from: string, to: string) {
    setDateFrom(from)
    setDateTo(to)
  }

  function resetFilters() {
    setSpecializations([])
    setDateFrom('')
    setDateTo('')
  }

  const hasActiveFilters = specializations.length > 0 || Boolean(dateFrom || dateTo)

  return {
    specializations,
    setSpecializations,
    dateFrom,
    dateTo,
    handlePeriodChange,
    hasActiveFilters,
    resetFilters,
    dashboardQuery,
    exportCsv,
    exportXlsx,
  }
}
