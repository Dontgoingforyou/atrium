import type { BenchCards as BenchCardsData } from '../../../types/bench'
import styles from '@/styles/modules/analytics/AnalyticsBenchPage.module.css'

type Props = {
  cards: BenchCardsData
}

function formatNumber(value: number | null): string {
  if (value === null || Number.isNaN(value)) return '—'
  return new Intl.NumberFormat('ru-RU').format(value)
}

export function BenchCards({ cards }: Props) {
  const items = [
    { label: 'Средняя ставка', value: formatNumber(cards.avg_rate) },
    { label: 'Time to Hire, дни', value: formatNumber(cards.avg_time_to_hire_days) },
    { label: 'Офферы', value: formatNumber(cards.offers) },
    { label: 'Конверсия офферов', value: `${formatNumber(cards.offer_conversion)}%` },
    { label: 'Выходы', value: formatNumber(cards.project_starts) },
  ]
  return (
    <div className={styles.cards}>
      {items.map((item) => (
        <article key={item.label} className={styles.card}>
          <p className={styles.cardLabel}>{item.label}</p>
          <p className={styles.cardValue}>{item.value}</p>
        </article>
      ))}
    </div>
  )
}
