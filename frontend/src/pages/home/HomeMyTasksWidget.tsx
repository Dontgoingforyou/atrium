import { Link } from 'react-router'
import { HomeTaskOpenCharts } from '../../components/home/HomeTaskOpenCharts'
import styles from '@/styles/modules/home/HomePage.module.css'
import { buildMyOverdueTasksPath } from '../tasks/tasksPageUrl'
import { CountBadge } from './HomeKpi'
import kpiStyles from '@/styles/modules/home/HomeKpi.module.css'

const MY_OPEN_HINT =
  'Назначенные вам и созданные вами без исполнителя (без колонок, исключённых из KPI)'

export function HomeMyTasksWidget({
  openCount,
  overdueCount,
}: {
  openCount: number
  overdueCount: number
}) {
  return (
    <section className={styles.section} data-tour="home-my-tasks">
      <div className={styles.widgetHeader}>
        <div className={styles.widgetHeaderMain}>
          <h2 className="section-heading" title={MY_OPEN_HINT}>
            Мои задачи
          </h2>
          <Link to="/tasks" className={kpiStyles.badgeLink} title={MY_OPEN_HINT}>
            <CountBadge label={`${openCount} открытых`} tone="info" />
          </Link>
          {overdueCount > 0 ? (
            <Link to={buildMyOverdueTasksPath()} className={kpiStyles.badgeLink}>
              <CountBadge label={`${overdueCount} просрочено`} tone="danger" />
            </Link>
          ) : null}
        </div>
        <nav className={styles.widgetHeaderPanel} aria-label="Действия: мои задачи">
          <Link to="/tasks" className={`${styles.widgetHeaderPanelBtn} ${styles.widgetHeaderPanelBtnGhost}`}>
            Все задачи →
          </Link>
          <Link
            to="/tasks?view=kanban"
            className={`${styles.widgetHeaderPanelBtn} ${styles.widgetHeaderPanelBtnGhost}`}
            data-tour="home-kanban"
          >
            Канбан →
          </Link>
        </nav>
      </div>
      {openCount > 0 || overdueCount > 0 ? (
        <div className={styles.myTasksCharts}>
          <HomeTaskOpenCharts
            title="Мои открытые"
            openCount={openCount}
            overdueCount={overdueCount}
            byPriority={null}
            overdueTo={buildMyOverdueTasksPath()}
          />
        </div>
      ) : (
        <p className={`text-muted ${styles.textSmall}`}>Нет открытых задач</p>
      )}
    </section>
  )
}
