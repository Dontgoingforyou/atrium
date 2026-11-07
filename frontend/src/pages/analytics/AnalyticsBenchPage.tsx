import { BenchCards } from './bench/BenchCards'
import { BenchCharts } from './bench/BenchCharts'
import { BenchFilters } from './bench/BenchFilters'
import { BenchTables } from './bench/BenchTables'
import { useAnalyticsBenchPageController } from './bench/useAnalyticsBenchPageController'
import styles from '@/styles/modules/analytics/AnalyticsBenchPage.module.css'

export function AnalyticsBenchPage() {
  const ctrl = useAnalyticsBenchPageController()
  const { dashboardQuery, exportCsv, exportXlsx } = ctrl
  const data = dashboardQuery.data

  return (
    <div>
      {data?.is_stale && data.stale_message && (
        <div className={styles.staleBanner} role="status">
          {data.stale_message}
        </div>
      )}
      <BenchFilters
        specializationsSelected={ctrl.specializations}
        onSpecializationsChange={ctrl.setSpecializations}
        specializations={data?.specializations ?? []}
        dateFrom={ctrl.dateFrom}
        dateTo={ctrl.dateTo}
        onPeriodChange={ctrl.handlePeriodChange}
        hasActiveFilters={ctrl.hasActiveFilters}
        onReset={ctrl.resetFilters}
      />
      <div className={styles.exportBar}>
        <button
          type="button"
          className="btn-secondary"
          onClick={() => exportCsv.mutate()}
          disabled={exportCsv.isPending}
        >
          Скачать CSV
        </button>
        <button
          type="button"
          className="btn-secondary"
          onClick={() => exportXlsx.mutate()}
          disabled={exportXlsx.isPending}
        >
          Скачать XLSX
        </button>
      </div>
      {dashboardQuery.isPending && <p className="text-muted">Загрузка сводки…</p>}
      {dashboardQuery.isError && (
        <p className={styles.errorText}>Не удалось загрузить дашборд бенч. Попробуйте обновить страницу.</p>
      )}
      {data && !dashboardQuery.isPending && (
        <>
          <BenchCards cards={data.cards} />
          <BenchCharts data={data} />
          <BenchTables data={data} />
        </>
      )}
    </div>
  )
}
