import { useQuery } from '@tanstack/react-query'
import { fetchHome } from '../../api/homeApi'
import { PORTAL_HOME_QUERY_KEY, PORTAL_TASK_COLUMNS_QUERY_KEY } from '../../api/queryKeys'
import { listTaskColumns } from '../../api/tasks/tasksApi'
import { useAuthStore } from '../../store/authStore'
import { UserAvatar } from '../../components/ui/UserAvatar'
import { userFacingMessageFromUnknown } from '../../utils/apiUserMessage'
import styles from '@/styles/modules/home/HomePage.module.css'
import { HomeAdminDashboardWidget } from './HomeAdminDashboardWidget'
import { HomeFavoritesWidget } from './HomeFavoritesWidget'
import { HomeManagerWidget } from './HomeManagerWidget'
import { HomeMyTasksWidget } from './HomeMyTasksWidget'

export function HomePage() {
  const user = useAuthStore((s) => s.user)
  const { data, isPending, isError, error } = useQuery({
    queryKey: PORTAL_HOME_QUERY_KEY,
    queryFn: () => fetchHome(),
  })
  const columnsQuery = useQuery({
    queryKey: PORTAL_TASK_COLUMNS_QUERY_KEY,
    queryFn: () => listTaskColumns(),
    staleTime: 60_000,
    enabled: Boolean(data?.admin || data?.manager),
  })
  const taskColumns = columnsQuery.data ?? []

  return (
    <div>
      <h1 className={`page-title ${styles.pageTitleCompact}`}>Главная</h1>
      <p className={styles.intro}>
        <UserAvatar
          size={40}
          label={user?.full_name || user?.email || '—'}
          imageUrl={user?.avatar_url}
          className={styles.introAvatar}
        />
        <span>
          Вы вошли как <strong>{user?.full_name || user?.email || '—'}</strong>
          {user?.is_portal_admin ? ' (администратор портала)' : ''}
        </span>
      </p>

      {isPending ? (
        <p className="text-muted">Загрузка…</p>
      ) : isError ? (
        <p className="text-danger">{userFacingMessageFromUnknown(error)}</p>
      ) : (
        <div className={styles.page}>
          <HomeFavoritesWidget favorites={data.favorites_preview} />
          {columnsQuery.isError ? (
            <p className="text-danger">{userFacingMessageFromUnknown(columnsQuery.error)}</p>
          ) : null}
          {data.admin ? <HomeAdminDashboardWidget block={data.admin} columns={taskColumns} /> : null}
          <HomeMyTasksWidget
            openCount={data.my_tasks_open_count}
            overdueCount={data.my_tasks_overdue_count}
          />
          {data.manager ? <HomeManagerWidget block={data.manager} columns={taskColumns} /> : null}
        </div>
      )}
    </div>
  )
}
