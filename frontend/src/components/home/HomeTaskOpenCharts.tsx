import { Link } from 'react-router'
import { useAnimatedNumber } from '../../hooks/useAnimatedNumber'
import { PRIORITY_LABELS } from '../../domain/tasks/taskUi'
import type { TaskPriority } from '../../types/task'
import type { TaskOpenByPriority } from '../../types/home'
import type { TimeEntryReportBucket } from '../../types/timeEntry'
import { formatMinutes } from '@/utils/time/timeEntryUtils'
import chartStyles from '@/styles/modules/home/HomeTaskOpenCharts.module.css'

const PRI_ORDER: TaskPriority[] = ['high', 'medium', 'low']

/** Норма для визуальной шкалы: 40 ч в месяц = заполнение «полная полоса». */
const TIMESHEET_VISUAL_CAP_MINUTES = 40 * 60

type HomeTaskOpenChartsProps = {
  openCount: number
  overdueCount: number
  /** Если null — только кольцо сроков (без полос приоритетов). */
  byPriority: TaskOpenByPriority | null
  /** Заголовок блока (например «Команда» / «Разделы») */
  title?: string
  /** Показать условную шкалу таймшитов (минуты за месяц) */
  timesheetMinutes?: number
  /** Бакеты по неделям для мини-бар-чарта */
  weeklyBuckets?: TimeEntryReportBucket[]
  /** Канбан просроченных; без него легенда «Просрочено» остаётся текстом */
  overdueTo?: string
  overdueLinkState?: unknown
}

export function HomeTaskOpenCharts({
  openCount,
  overdueCount,
  byPriority,
  title = 'Открытые задачи',
  timesheetMinutes,
  weeklyBuckets,
  overdueTo,
  overdueLinkState,
}: HomeTaskOpenChartsProps) {
  const animOpen = useAnimatedNumber(openCount)
  const animOverdue = useAnimatedNumber(overdueCount)
  const animOnTrack = Math.max(0, animOpen - animOverdue)

  const displayOpen = Math.round(animOpen)
  const displayOverdue = Math.round(animOverdue)
  const displayOnTrack = Math.max(0, displayOpen - displayOverdue)

  const overduePct = animOpen > 0 ? (animOverdue / animOpen) * 100 : 0
  const onTrackPct = animOpen > 0 ? (animOnTrack / animOpen) * 100 : 0
  const angleOverdue = (overduePct / 100) * 360
  const donutBackground =
    animOpen <= 0.01
      ? 'conic-gradient(var(--color-bg-subtle) 0deg 360deg)'
      : `conic-gradient(var(--color-danger-ui) 0deg ${angleOverdue}deg, var(--color-success) ${angleOverdue}deg 360deg)`

  const animPriHigh = useAnimatedNumber(byPriority?.high ?? 0)
  const animPriMedium = useAnimatedNumber(byPriority?.medium ?? 0)
  const animPriLow = useAnimatedNumber(byPriority?.low ?? 0)
  const animPriByKey: Record<TaskPriority, number> = {
    high: animPriHigh,
    medium: animPriMedium,
    low: animPriLow,
  }
  const displayPriByKey: Record<TaskPriority, number> = {
    high: Math.round(animPriHigh),
    medium: Math.round(animPriMedium),
    low: Math.round(animPriLow),
  }

  const priTotal = animPriHigh + animPriMedium + animPriLow
  const timesheetFillPct =
    timesheetMinutes === undefined
      ? 0
      : Math.min(100, (timesheetMinutes / TIMESHEET_VISUAL_CAP_MINUTES) * 100)
  const animTimesheetFill = useAnimatedNumber(timesheetFillPct)

  const weeklySeries: TimeEntryReportBucket[] | null =
    weeklyBuckets !== undefined && weeklyBuckets.length > 0 ? weeklyBuckets : null
  const weeklyMax = weeklySeries ? Math.max(...weeklySeries.map((b) => b.total_minutes), 1) : 1

  const compactLayout = byPriority === null && timesheetMinutes === undefined && weeklySeries === null

  return (
    <div className={chartStyles.chartsWrap}>
      <h3 className={chartStyles.chartsTitle}>
        <span key={title} className={chartStyles.chartsTitleText}>
          {title}
        </span>
      </h3>
      <div className={compactLayout ? chartStyles.chartsStack : chartStyles.chartsGrid}>
        <div className={chartStyles.donutCard}>
          <div
            className={chartStyles.donut}
            style={{ background: donutBackground }}
            role="img"
            aria-label={`Открытых ${displayOpen}, просрочено ${displayOverdue}`}
          />
          <ul className={chartStyles.donutLegend}>
            <li>
              <span className={`${chartStyles.legendSwatch} ${chartStyles.swatchDanger}`} />
              {overdueTo ? (
                <Link
                  to={overdueTo}
                  state={overdueLinkState}
                  className={`${chartStyles.legendEntry} ${chartStyles.legendOverdueLink}`}
                  aria-label="Открыть просроченные задачи"
                  title="Открыть просроченные задачи"
                >
                  <span>Просрочено:</span>
                  <strong className={chartStyles.legendValue}>{displayOverdue}</strong>
                </Link>
              ) : (
                <span className={chartStyles.legendEntry}>
                  <span>Просрочено:</span>
                  <strong className={chartStyles.legendValue}>{displayOverdue}</strong>
                </span>
              )}
            </li>
            <li>
              <span className={`${chartStyles.legendSwatch} ${chartStyles.swatchSuccess}`} />
              <span className={chartStyles.legendEntry}>
                <span>В срок:</span>
                <strong className={chartStyles.legendValue}>{displayOnTrack}</strong>
              </span>
            </li>
          </ul>
          {animOpen > 0.01 ? (
            <div className={chartStyles.stackedBar} aria-hidden>
              <div className={chartStyles.stackedOverdue} style={{ width: `${overduePct}%` }} />
              <div className={chartStyles.stackedOnTrack} style={{ width: `${onTrackPct}%` }} />
            </div>
          ) : null}
        </div>
        {!compactLayout ? (
          <div className={chartStyles.priorityCard}>
            {byPriority === null ? null : byPriority.high + byPriority.medium + byPriority.low === 0 ? (
              <p className={`text-muted ${chartStyles.emptyPriority}`}>
                Нет открытых задач для разбивки по приоритету
              </p>
            ) : (
              <div className={chartStyles.priorityRows}>
                {PRI_ORDER.map((key) => {
                  const nAnim = animPriByKey[key]
                  const pct = priTotal > 0 ? (nAnim / priTotal) * 100 : 0
                  const fillClass =
                    key === 'high'
                      ? chartStyles.priorityFillHigh
                      : key === 'medium'
                        ? chartStyles.priorityFillMedium
                        : chartStyles.priorityFillLow
                  return (
                    <div key={key} className={chartStyles.priorityRow}>
                      <span className={chartStyles.priorityLabel}>{PRIORITY_LABELS[key]}</span>
                      <div className={chartStyles.priorityBarTrack}>
                        <div
                          className={`${chartStyles.priorityBarFill} ${fillClass}`}
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                      <span className={chartStyles.priorityValue}>{displayPriByKey[key]}</span>
                    </div>
                  )
                })}
              </div>
            )}
            {timesheetMinutes !== undefined && weeklySeries === null ? (
              <div className={chartStyles.timesheetBarWrap}>
                <div className={chartStyles.timesheetBarLabel}>
                  Трудозатраты за месяц (до ~40 ч как ориентир на шкале)
                </div>
                <div className={chartStyles.timesheetBarTrack} aria-hidden>
                  <div
                    className={chartStyles.timesheetBarFill}
                    style={{ width: `${animTimesheetFill}%` }}
                  />
                </div>
              </div>
            ) : null}
            {weeklySeries ? (
              <div className={chartStyles.weeklyBarsWrap}>
                <div className={chartStyles.weeklyBarsLabel}>Трудозатраты по неделям</div>
                <div className={chartStyles.weeklyBars} role="list" aria-label="Таймшиты по неделям">
                  {weeklySeries.map((b) => {
                    const heightPct = Math.max(4, (b.total_minutes / weeklyMax) * 100)
                    const label = formatMinutes(b.total_minutes)
                    return (
                      <div
                        key={b.period_label}
                        className={chartStyles.weeklyBarCol}
                        role="listitem"
                        aria-label={`${b.period_label}: ${label}`}
                      >
                        <div
                          className={chartStyles.weeklyBar}
                          style={{ height: `${heightPct}%` }}
                          title={`${b.period_label}: ${label}`}
                        />
                        <span className={chartStyles.weeklyBarTick} aria-hidden>
                          {b.period_label.slice(-3)}
                        </span>
                      </div>
                    )
                  })}
                </div>
              </div>
            ) : null}
          </div>
        ) : null}
      </div>
    </div>
  )
}
