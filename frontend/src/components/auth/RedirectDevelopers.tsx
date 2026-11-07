import { Navigate, Outlet } from 'react-router'

import { useAuthStore } from '../../store/authStore'
import { isTimesheetOnlyUser } from '@/domain/auth/authRoles'

/**
 * Layout-route: если текущий пользователь — только таймшиты (students / au_specialist и т.п.),
 * перенаправляет на /analytics/timesheets.
 * При наличии нескольких ролей (students + outstaff / admin) приоритет у старшей роли,
 * кроме должностей с ограничением «только ТШ».
 */
export function RedirectDevelopers() {
  const user = useAuthStore((s) => s.user)
  if (
    user &&
    isTimesheetOnlyUser(user)
  ) {
    return <Navigate to="/analytics/timesheets" replace />
  }
  return <Outlet />
}
