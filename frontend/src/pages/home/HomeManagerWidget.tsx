import { Link } from 'react-router'
import { HomeTaskOpenCharts } from '../../components/home/HomeTaskOpenCharts'
import type { HomeManagerBlock } from '../../types/home'
import type { PortalTaskColumn } from '../../types/task'
import { formatMinutes } from '@/utils/time/timeEntryUtils'
import styles from '@/styles/modules/home/HomePage.module.css'
import { homeDashboardNavState } from '../tasks/taskBackNav'
import {
  buildTeamDoneThisMonthTasksPath,
  buildTeamNoAssigneeTasksPath,
  buildTeamOpenTasksPath,
  buildTeamOverdueTasksPath,
} from '../tasks/tasksPageUrl'
import { KpiCard } from './HomeKpi'
import { HomeTaskRow } from './HomeTaskRow'

export function HomeManagerWidget({
  block,
  columns,
}: {
  block: HomeManagerBlock
  columns: PortalTaskColumn[]
}) {
  const ts = block.timesheet_current_month
  return (
    <section className={styles.section} data-tour="home-manager-panel">
      <div className={styles.widgetHeader}>
        <div className={styles.widgetHeaderMain}>
          <h2 className="section-heading">Панель руководителя</h2>
        </div>
        <nav className={styles.widgetHeaderPanel} aria-label="Действия: панель руководителя">
          <Link
            to="/tasks?scope=team"
            state={homeDashboardNavState()}
            className={`${styles.widgetHeaderPanelBtn} ${styles.widgetHeaderPanelBtnGhost}`}
          >
            Задачи команды →
          </Link>
        </nav>
      </div>

      <div className={styles.kpiGrid}>
        <KpiCard
          label="Открытых задач"
          value={block.section_open_count}
          title="Открыть задачи разделов, как в счётчике «Открытых задач»"
          to={buildTeamOpenTasksPath()}
          linkState={homeDashboardNavState()}
        />
        <KpiCard
          label="Просрочено"
          value={block.section_overdue_count}
          tone={block.section_overdue_count > 0 ? 'danger' : 'default'}
          title="Открыть просроченные задачи разделов"
          to={buildTeamOverdueTasksPath()}
          linkState={homeDashboardNavState()}
        />
        <KpiCard
          label="Закрыто в этом месяце"
          value={block.section_done_this_month}
          tone="accent"
          title="Открыть задачи разделов, закрытые в этом месяце"
          to={buildTeamDoneThisMonthTasksPath()}
          linkState={homeDashboardNavState()}
        />
        <KpiCard
          label="Без исполнителя"
          value={block.section_no_assignee_count}
          tone={block.section_no_assignee_count > 0 ? 'warn' : 'default'}
          title="Открыть задачи разделов без исполнителя"
          to={buildTeamNoAssigneeTasksPath()}
          linkState={homeDashboardNavState()}
        />
      </div>

      <div className={styles.dashboardSplit}>
        <HomeTaskOpenCharts
          title="Разделы: сроки и приоритеты"
          openCount={block.section_open_count}
          overdueCount={block.section_overdue_count}
          byPriority={block.section_open_by_priority}
          weeklyBuckets={block.timesheet_weekly_buckets.length > 0 ? block.timesheet_weekly_buckets : undefined}
        />
        <div className={styles.dashboardColMain}>
          <div className={styles.timesheetKpi}>
            <span className={styles.timesheetKpiLabel}>Мои таймшиты (с 1-го числа месяца)</span>
            <span className={styles.timesheetKpiValue}>{formatMinutes(ts.total_minutes)}</span>
            <span className={styles.timesheetKpiMeta}>{ts.entries_count} записей</span>
            <span className={styles.timesheetKpiMeta}>
              В работе: {block.section_by_status.in_progress} · В очереди: {block.section_by_status.todo}
            </span>
          </div>
          {block.section_tasks_preview.length === 0 ? (
            <p className={`text-muted ${styles.textSmall}`}>Нет задач в доступных разделах</p>
          ) : (
            <div className={styles.taskList}>
              {block.section_tasks_preview.slice(0, 5).map((t) => (
                <HomeTaskRow key={t.id} task={t} columns={columns} />
              ))}
            </div>
          )}
        </div>
      </div>
    </section>
  )
}
