import { Navigate, NavLink, Outlet, useLocation } from 'react-router'
import { useAuthStore } from '../../store/authStore'
import { isTimesheetOnlyUser, isUserManagerOrAdmin } from '@/domain/auth/authRoles'
import tabStyles from '@/styles/modules/common/Tabs.module.css'

function tabClass({ isActive }: { isActive: boolean }) {
  return `${tabStyles.tab} ${isActive ? tabStyles.tabActive : ''}`
}

export function AnalyticsLayout() {
  const user = useAuthStore((s) => s.user)
  const location = useLocation()
  const timesheetOnly = user
    ? isTimesheetOnlyUser(user)
    : false

  if (
    timesheetOnly &&
    (location.pathname === '/analytics' ||
      location.pathname.startsWith('/analytics/reports') ||
      location.pathname.startsWith('/analytics/bench'))
  ) {
    return <Navigate to="/analytics/timesheets" replace />
  }

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Аналитика</h1>
      </div>
      <nav className={tabStyles.tabs} aria-label="Разделы аналитики" data-tour="analytics-tabs">
        <NavLink to="/analytics/timesheets" className={tabClass}>
          Таймшиты
        </NavLink>
        {!timesheetOnly && (
          <NavLink to="/analytics/reports" className={tabClass}>
            Отчёты
          </NavLink>
        )}
        {user && isUserManagerOrAdmin(user) && (
          <NavLink to="/analytics/bench" className={tabClass}>
            Бенч
          </NavLink>
        )}
      </nav>
      <Outlet />
    </div>
  )
}
