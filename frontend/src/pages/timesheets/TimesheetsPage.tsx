import { useAuthStore } from '../../store/authStore'
import { isTimesheetOnlyUser, isUserManagerOrAdmin } from '@/domain/auth/authRoles'
import { CurrentMonthTimesheetCard } from './CurrentMonthTimesheetCard'
import { ManagerTimesheetView } from './ManagerTimesheetView'
import { DeveloperTimesheetView } from './DeveloperTimesheetView'

export function TimesheetsPage() {
  const user = useAuthStore((s) => s.user)
  const timesheetOnly = user
    ? isTimesheetOnlyUser(user)
    : false
  const isManager = user
    ? isUserManagerOrAdmin(user)
    : false

  return (
    <>
      <CurrentMonthTimesheetCard />
      {timesheetOnly ? <DeveloperTimesheetView /> : null}
      {isManager ? <ManagerTimesheetView /> : null}
    </>
  )
}
