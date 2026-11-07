import { useState } from 'react'
import { Link, useLocation } from 'react-router'
import { useQuery } from '@tanstack/react-query'
import { fetchHome } from '../../api/homeApi'
import { HomeTaskOpenCharts } from '../../components/home/HomeTaskOpenCharts'
import { userFacingMessageFromUnknown } from '../../utils/apiUserMessage'
import type { HomeAdminBlock } from '../../types/home'
import type { PortalTaskColumn } from '../../types/task'
import styles from '@/styles/modules/home/HomePage.module.css'
import {
  getHomeDashboardRestore,
  homeDashboardNavState,
  type HomeDashboardListMode,
} from '../tasks/taskBackNav'
import {
  buildTeamAssigneeOverdueTasksPath,
  buildTeamDoneThisMonthTasksPath,
  buildTeamNoAssigneeTasksPath,
  buildTeamOpenTasksPath,
  buildTeamOverdueTasksPath,
} from '../tasks/tasksPageUrl'
import { HomeAssigneeDrilldownPanel } from './HomeAssigneeDrilldownPanel'
import { HomeAssigneeDrilldownShell } from './HomeAssigneeDrilldownShell'
import { HomeAssigneeLoadWidget } from './HomeAssigneeLoadWidget'
import { KpiCard } from './HomeKpi'
import { homeQueryKeys } from './homeQueryKeys'

function initialFromLocation(state: unknown): {
  assigneeSub: string | null
  listMode: HomeDashboardListMode
  statusKeys: string[]
} {
  const restore = getHomeDashboardRestore(state)
  return {
    assigneeSub: restore?.homeAssigneeSub ?? null,
    listMode: restore?.homeListMode ?? 'all',
    statusKeys: restore?.homeStatusKeys ?? [],
  }
}

export function HomeAdminDashboardWidget({
  block,
  columns,
}: {
  block: HomeAdminBlock
  columns: PortalTaskColumn[]
}) {
  const location = useLocation()
  const initial = initialFromLocation(location.state)
  const [assigneeSub, setAssigneeSub] = useState<string | null>(initial.assigneeSub)
  const [listMode, setListMode] = useState<HomeDashboardListMode>(initial.listMode)
  const [statusKeys, setStatusKeys] = useState<string[]>(initial.statusKeys)

  const drilldownQuery = useQuery({
    queryKey: homeQueryKeys.assignee(assigneeSub ?? ''),
    queryFn: () => fetchHome(assigneeSub!),
    enabled: Boolean(assigneeSub),
  })

  const drilldown = drilldownQuery.data?.assignee_drilldown
  const chartTitle =
    assigneeSub && drilldown?.display_name
      ? `${drilldown.display_name}: сроки и приоритеты`
      : 'Команда: сроки и приоритеты'
  const chartOpenCount = assigneeSub && drilldown ? drilldown.open_count : block.team_open_count
  const chartOverdueCount = assigneeSub && drilldown ? drilldown.overdue_count : block.team_overdue_count
  const chartByPriority =
    assigneeSub && drilldown ? drilldown.open_by_priority : block.team_open_by_priority

  function selectAssignee(sub: string) {
    setAssigneeSub((prev) => (prev === sub ? null : sub))
    setListMode('all')
    setStatusKeys([])
  }

  function closeDrilldown() {
    setAssigneeSub(null)
    setListMode('all')
    setStatusKeys([])
  }

  return (
    <section className={styles.section} data-tour="home-admin-dashboard">
      <div className={styles.widgetHeader}>
        <div className={styles.widgetHeaderMain}>
          <h2 className="section-heading">Дашборд администратора</h2>
        </div>
        <nav className={styles.widgetHeaderPanel} aria-label="Действия: дашборд администратора">
          <Link
            to="/tasks/new"
            className={`${styles.widgetHeaderPanelBtn} ${styles.widgetHeaderPanelBtnPrimary}`}
            data-tour="home-new-task"
          >
            + Задача
          </Link>
          <Link
            to="/tasks?scope=team"
            state={homeDashboardNavState()}
            className={`${styles.widgetHeaderPanelBtn} ${styles.widgetHeaderPanelBtnGhost}`}
          >
            Задачи команды →
          </Link>
          <Link
            to="/specialists"
            className={`${styles.widgetHeaderPanelBtn} ${styles.widgetHeaderPanelBtnGhost}`}
          >
            Специалисты →
          </Link>
        </nav>
      </div>

      <div className={styles.kpiGrid}>
        <KpiCard
          label="Открытых задач"
          value={block.team_open_count}
          tone="info"
          title="Открыть задачи команды, как в счётчике «Открытых задач»"
          to={buildTeamOpenTasksPath()}
          linkState={homeDashboardNavState()}
        />
        <KpiCard
          label="Просрочено"
          value={block.team_overdue_count}
          tone={block.team_overdue_count > 0 ? 'danger' : 'default'}
          title="Открыть задачи команды с фильтром «просроченные»"
          to={buildTeamOverdueTasksPath()}
          linkState={homeDashboardNavState()}
        />
        <KpiCard
          label="Закрыто в этом месяце"
          value={block.team_done_this_month}
          tone="accent"
          title="Открыть задачи команды, закрытые в этом месяце"
          to={buildTeamDoneThisMonthTasksPath()}
          linkState={homeDashboardNavState()}
        />
        <KpiCard
          label="Без исполнителя"
          value={block.team_no_assignee_count}
          tone={block.team_no_assignee_count > 0 ? 'warn' : 'default'}
          title="Открыть задачи команды без исполнителя"
          to={buildTeamNoAssigneeTasksPath()}
          linkState={homeDashboardNavState()}
        />
      </div>

      <div className={styles.dashboardStack}>
        <HomeTaskOpenCharts
          title={chartTitle}
          openCount={chartOpenCount}
          overdueCount={chartOverdueCount}
          byPriority={chartByPriority}
          overdueTo={
            assigneeSub ? buildTeamAssigneeOverdueTasksPath(assigneeSub) : buildTeamOverdueTasksPath()
          }
          overdueLinkState={homeDashboardNavState()}
        />
        <div className={styles.dashboardColMain}>
          {block.team_assignee_load.length > 0 ? (
            <HomeAssigneeLoadWidget
              rows={block.team_assignee_load}
              selectedSub={assigneeSub}
              onSelect={selectAssignee}
            />
          ) : null}
          <HomeAssigneeDrilldownShell
            open={Boolean(assigneeSub)}
            loading={drilldownQuery.isPending}
            isError={drilldownQuery.isError}
            errorMessage={
              drilldownQuery.isError ? userFacingMessageFromUnknown(drilldownQuery.error) : undefined
            }
            data={drilldownQuery.data?.assignee_drilldown}
          >
            {(dd) => (
              <HomeAssigneeDrilldownPanel
                data={dd}
                columns={columns}
                listMode={listMode}
                statusKeys={statusKeys}
                onListModeChange={setListMode}
                onStatusKeysChange={setStatusKeys}
                onClose={closeDrilldown}
              />
            )}
          </HomeAssigneeDrilldownShell>
        </div>
      </div>
    </section>
  )
}
