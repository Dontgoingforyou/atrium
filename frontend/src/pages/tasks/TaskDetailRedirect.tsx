import { Navigate, useParams } from 'react-router'

import { buildTasksPageUrlWithTask, TASK_ID_FROM_URL_RE } from './tasksPageUrl'

export function TaskDetailRedirect() {
  const { taskId } = useParams<{ taskId: string }>()
  if (!taskId || !TASK_ID_FROM_URL_RE.test(taskId)) {
    return <Navigate to="/tasks" replace />
  }
  return <Navigate to={buildTasksPageUrlWithTask(taskId)} replace />
}
