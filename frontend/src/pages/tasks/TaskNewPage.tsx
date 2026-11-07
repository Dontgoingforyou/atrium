import { Link, useLocation, useNavigate } from 'react-router'
import { useQueryClient } from '@tanstack/react-query'
import { useMemo } from 'react'
import { CreateTaskForm } from './CreateTaskForm'
import { PORTAL_TASKS_ROOT_QUERY_KEY } from './tasksQueryKeys'
import { useAuthStore } from '../../store/authStore'
import { useTourStore } from '../../onboarding/tourStore'
import type { TourDemoTaskPrefill } from '../../onboarding/ensureTourDemoTask'
import backBtnStyles from '@/styles/modules/tasks/TaskBackButton.module.css'
import styles from '@/styles/modules/tasks/TaskDetailPage.module.css'

interface NewTaskNavState {
  initialStatus?: string
  initialAssigneeSubs?: string[]
  tourDemo?: TourDemoTaskPrefill
}

export function TaskNewPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const location = useLocation()
  const user = useAuthStore((s) => s.user)
  const storePrefill = useTourStore((s) => s.demoTaskPrefill)

  const state = (location.state ?? {}) as NewTaskNavState

  const tourDemo = state.tourDemo ?? storePrefill ?? undefined

  const initialAssigneeSubs = useMemo(() => {
    if (tourDemo?.assigneeSubs && tourDemo.assigneeSubs.length > 0) {
      return tourDemo.assigneeSubs
    }
    if (state.initialAssigneeSubs && state.initialAssigneeSubs.length > 0) {
      return state.initialAssigneeSubs
    }
    return user ? [user.sub] : []
  }, [tourDemo?.assigneeSubs, state.initialAssigneeSubs, user])

  return (
    <div className={styles.page}>
      <div className={styles.toolbar}>
        <button type="button" className={backBtnStyles.backBtn} onClick={() => navigate(-1)}>
          ← Назад
        </button>
        <div className={styles.toolbarActions}>
          <Link to="/" className={styles.linkMuted}>
            На главную
          </Link>
          <Link to="/tasks" className={styles.linkMuted}>
            Все задачи
          </Link>
        </div>
      </div>
      <h1 className="page-title">Новая задача</h1>
      <CreateTaskForm
        initialStatus={state.initialStatus ?? 'todo'}
        initialAssigneeSubs={initialAssigneeSubs}
        tourDemo={tourDemo}
        onCreated={(created) => {
          void queryClient.invalidateQueries({ queryKey: PORTAL_TASKS_ROOT_QUERY_KEY })
          if (created) navigate(`/tasks/${encodeURIComponent(created.id)}`, { replace: true })
        }}
      />
    </div>
  )
}
