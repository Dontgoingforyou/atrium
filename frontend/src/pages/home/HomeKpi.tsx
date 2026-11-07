import { Link } from 'react-router'
import styles from '@/styles/modules/home/HomeKpi.module.css'

export type CountBadgeTone = 'normal' | 'danger' | 'info' | 'circle'
export type KpiCardTone = 'default' | 'danger' | 'warn' | 'accent' | 'info'

const BADGE_TONE_CLASS: Record<CountBadgeTone, string> = {
  normal: styles.badgeNormal,
  danger: styles.badgeDanger,
  info: styles.badgeInfo,
  circle: styles.badgeCircle,
}

const KPI_TONE_CLASS: Record<KpiCardTone, string> = {
  default: styles.kpiCardDefault,
  danger: styles.kpiCardDanger,
  warn: styles.kpiCardWarn,
  accent: styles.kpiCardAccent,
  info: styles.kpiCardInfo,
}

export function CountBadge({
  label,
  tone = 'normal',
  title,
}: {
  label: string
  tone?: CountBadgeTone
  title?: string
}) {
  return (
    <span className={`${styles.badge} ${BADGE_TONE_CLASS[tone]}`} title={title}>
      {label}
    </span>
  )
}

export function KpiCard({
  label,
  value,
  tone = 'default',
  title,
  to,
  linkState,
}: {
  label: string
  value: number
  tone?: KpiCardTone
  title?: string
  /** Если задан — карточка-ссылка (например KPI → задачи). */
  to?: string
  linkState?: unknown
}) {
  const className = `${styles.kpiCard} ${KPI_TONE_CLASS[tone]}`
  const body = (
    <>
      <span className={styles.kpiCardValue}>{value}</span>
      <span className={styles.kpiCardLabel}>{label}</span>
    </>
  )
  if (to) {
    return (
      <Link to={to} state={linkState} className={`${className} ${styles.kpiCardLink}`} title={title}>
        {body}
      </Link>
    )
  }
  return (
    <div className={className} title={title}>
      {body}
    </div>
  )
}
