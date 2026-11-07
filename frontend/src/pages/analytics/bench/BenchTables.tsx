import { TagChip } from '../../../components/tags/TagChip'
import type { BenchDashboard } from '../../../types/bench'
import styles from '@/styles/modules/analytics/AnalyticsBenchPage.module.css'
import { conversionLevelColor } from './conversionLevel'

type Props = {
  data: BenchDashboard
}

function formatRate(value: number | null): string {
  if (value === null) return '—'
  return new Intl.NumberFormat('ru-RU').format(value)
}

function ConversionPill({ value }: { value: number }) {
  return (
    <TagChip storedColor={conversionLevelColor(value)} className={styles.conversionChip} border="soft">
      <span className={styles.conversionChipLabel}>{value}%</span>
    </TagChip>
  )
}

export function BenchTables({ data }: Props) {
  const years = data.monthly_summary.years
  return (
    <div className={styles.tables}>
      <section className={styles.tableCard}>
        <h2 className={styles.sectionTitle}>По специализациям</h2>
        <div className={styles.tableWrap}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Специализация</th>
                <th>Ставка</th>
                <th>CV</th>
                <th>Офферы</th>
                <th>Выходы</th>
                <th>Отказы</th>
                <th>Конв. оффер</th>
                <th>Конв. выход</th>
              </tr>
            </thead>
            <tbody>
              {data.specialization_stats.map((row) => (
                <tr key={row.specialization}>
                  <td>{row.specialization}</td>
                  <td>{formatRate(row.avg_rate)}</td>
                  <td>{row.cv_sent}</td>
                  <td>{row.offers}</td>
                  <td>{row.project_starts}</td>
                  <td>{row.rejections}</td>
                  <td className={styles.conversionCell}>
                    <ConversionPill value={row.offer_conversion} />
                  </td>
                  <td className={styles.conversionCell}>
                    <ConversionPill value={row.project_conversion} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
      <section className={styles.tableCard}>
        <h2 className={styles.sectionTitle}>Сводка по месяцам</h2>
        <div className={styles.tableWrap}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Месяц</th>
                {years.map((year) => (
                  <th key={`o-${year}`}>Офферы {year}</th>
                ))}
                {years.map((year) => (
                  <th key={`s-${year}`}>Выходы {year}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.monthly_summary.rows.map((row) => (
                <tr key={row.month}>
                  <td>{row.month}</td>
                  {years.map((year) => (
                    <td key={`o-${row.month}-${year}`}>{row.by_year[String(year)]?.offers ?? 0}</td>
                  ))}
                  {years.map((year) => (
                    <td key={`s-${row.month}-${year}`}>{row.by_year[String(year)]?.starts ?? 0}</td>
                  ))}
                </tr>
              ))}
              {years.length > 0 && (
                <tr>
                  <td>Итого</td>
                  {years.map((year) => (
                    <td key={`to-${year}`}>{data.monthly_summary.totals[String(year)]?.offers ?? 0}</td>
                  ))}
                  {years.map((year) => (
                    <td key={`ts-${year}`}>{data.monthly_summary.totals[String(year)]?.starts ?? 0}</td>
                  ))}
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}
