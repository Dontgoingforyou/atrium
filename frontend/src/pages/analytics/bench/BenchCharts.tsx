import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { TooltipContentProps } from 'recharts'

import type { BenchDashboard } from '../../../types/bench'
import styles from '@/styles/modules/analytics/AnalyticsBenchPage.module.css'

type Props = {
  data: BenchDashboard
}

const FUNNEL_LABELS: Record<string, string> = {
  cv_sent: 'CV',
  screening: 'Скрининг',
  internal_interview: 'Внутреннее',
  tech_stage_1: 'Тех. 1',
  final_stage: 'Финал',
  offers: 'Офферы',
  project_starts: 'Выходы',
}

const CHART_TOOLTIP_STYLE = {
  background: 'var(--color-bg-elevated)',
  border: '1px solid var(--color-border)',
  borderRadius: 'var(--radius-sm)',
  color: 'var(--color-text-primary)',
  boxShadow: 'var(--shadow-elev-3)',
}

const CHART_TICK = { fill: 'var(--color-text-muted)', fontSize: 12 }

const CHART_CURSOR_BAR = {
  fill: 'color-mix(in srgb, var(--color-accent) 18%, transparent)',
}

const CHART_CURSOR_LINE = {
  stroke: 'var(--color-accent)',
  strokeWidth: 1,
  strokeOpacity: 0.45,
}

function hoverBar(fill: string) {
  return { fill, stroke: 'none' }
}

function BenchMonthlyTooltip({ active, payload, label }: TooltipContentProps) {
  if (!active || !payload?.length) return null
  return (
    <div className={styles.monthlyTooltip}>
      <div className={styles.monthlyTooltipLabel}>{label}</div>
      <ul className={styles.monthlyTooltipList}>
        {payload.map((entry) => (
          <li key={String(entry.dataKey)} className={styles.monthlyTooltipItem}>
            <span
              className={styles.monthlyTooltipSwatch}
              style={{ backgroundColor: String(entry.color ?? 'var(--color-text-muted)') }}
            />
            <span className={styles.monthlyTooltipName}>{entry.name}</span>
            <span className={styles.monthlyTooltipValue}>{entry.value}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

export function BenchCharts({ data }: Props) {
  const funnel = Object.entries(data.funnel).map(([key, value]) => ({
    name: FUNNEL_LABELS[key] ?? key,
    value,
  }))
  return (
    <div className={styles.charts}>
      <section className={styles.chartCard}>
        <h2 className={styles.sectionTitle}>Воронка продаж специалистов</h2>
        <div className={styles.chartBody}>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={funnel}>
              <CartesianGrid stroke="var(--color-border-subtle)" vertical={false} />
              <XAxis dataKey="name" tick={CHART_TICK} />
              <YAxis tick={CHART_TICK} />
              <Tooltip
                contentStyle={CHART_TOOLTIP_STYLE}
                cursor={CHART_CURSOR_BAR}
                labelStyle={{ color: 'var(--color-heading)' }}
                itemStyle={{ color: 'var(--color-text-primary)' }}
              />
              <Legend />
              <Bar
                dataKey="value"
                fill="var(--color-accent)"
                name="Количество"
                cursor="pointer"
                activeBar={hoverBar('var(--color-accent-hover)')}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </section>
      <section className={styles.chartCard}>
        <h2 className={styles.sectionTitle}>Динамика по месяцам</h2>
        <div className={styles.chartBody}>
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={data.monthly_dynamics}>
              <CartesianGrid stroke="var(--color-border-subtle)" />
              <XAxis dataKey="label" tick={CHART_TICK} />
              <YAxis tick={CHART_TICK} />
              <Tooltip content={BenchMonthlyTooltip} cursor={CHART_CURSOR_LINE} />
              <Legend />
              <Line
                type="monotone"
                dataKey="cv_sent"
                name="CV"
                stroke="var(--color-bench-orange)"
                activeDot={{ fill: 'var(--color-bench-orange)', r: 5 }}
              />
              <Line
                type="monotone"
                dataKey="offers"
                name="Офферы"
                stroke="var(--color-accent)"
                activeDot={{ fill: 'var(--color-accent-hover)', r: 5 }}
              />
              <Line
                type="monotone"
                dataKey="project_starts"
                name="Выходы"
                stroke="var(--color-bench-chartreuse)"
                activeDot={{ fill: 'var(--color-bench-chartreuse)', r: 5 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </section>
      <section className={styles.chartCard}>
        <h2 className={styles.sectionTitle}>Конверсия по специализациям</h2>
        <div className={data.conversion_by_spec.length > 8 ? `${styles.chartBody} ${styles.chartBodyScroll}` : styles.chartBody}>
          <div className={data.conversion_by_spec.length > 8 ? styles.chartBodyWide : undefined}>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={data.conversion_by_spec}>
              <CartesianGrid stroke="var(--color-border-subtle)" vertical={false} />
              <XAxis dataKey="specialization" tick={CHART_TICK} interval={0} />
              <YAxis tick={CHART_TICK} />
              <Tooltip
                contentStyle={CHART_TOOLTIP_STYLE}
                cursor={CHART_CURSOR_BAR}
                labelStyle={{ color: 'var(--color-heading)' }}
                itemStyle={{ color: 'var(--color-text-primary)' }}
              />
              <Legend />
              <Bar
                dataKey="offer_conversion"
                name="Оффер %"
                fill="var(--color-accent)"
                cursor="pointer"
                activeBar={hoverBar('var(--color-accent-hover)')}
              />
              <Bar
                dataKey="project_conversion"
                name="Выход %"
                fill="var(--color-bench-chartreuse)"
                cursor="pointer"
                activeBar={hoverBar('var(--color-bench-chartreuse)')}
              />
            </BarChart>
          </ResponsiveContainer>
          </div>
        </div>
      </section>
      <section className={styles.chartCard}>
        <h2 className={styles.sectionTitle}>CV по специализациям</h2>
        <div className={styles.chartBody}>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={data.specialization_stats}>
              <CartesianGrid stroke="var(--color-border-subtle)" vertical={false} />
              <XAxis dataKey="specialization" tick={CHART_TICK} />
              <YAxis tick={CHART_TICK} />
              <Tooltip
                contentStyle={CHART_TOOLTIP_STYLE}
                cursor={CHART_CURSOR_BAR}
                labelStyle={{ color: 'var(--color-heading)' }}
                itemStyle={{ color: 'var(--color-text-primary)' }}
              />
              <Legend />
              <Bar
                dataKey="cv_sent"
                name="CV"
                fill="var(--color-bench-orange)"
                cursor="pointer"
                activeBar={hoverBar('var(--color-accent)')}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </section>
    </div>
  )
}
