import { useParams } from 'react-router'
import { Navigate } from 'react-router'
import { useQuery } from '@tanstack/react-query'
import { getTaskByNumber } from '@/api/tasks/tasksApi'
import { buildTasksPageUrlWithTask } from './tasksPageUrl'
import { taskByNumberQueryKey } from './tasksQueryKeys'

export function TaskByNumberRedirect() {
  const { taskNumber } = useParams<{ taskNumber: string }>()
  const number = taskNumber ? parseInt(taskNumber, 10) : NaN

  const { data: task, isLoading, isError } = useQuery({
    queryKey: taskByNumberQueryKey(number),
    queryFn: () => getTaskByNumber(number),
    enabled: !isNaN(number) && number > 0,
    staleTime: 60_000,
    retry: false,
  })

  if (isNaN(number) || number <= 0) {
    return <p className="text-muted">Некорректный номер задачи.</p>
  }

  if (isLoading) {
    return <p className="text-muted">Загрузка…</p>
  }

  if (isError || !task) {
    return <p className="text-danger">Задача #{number} не найдена.</p>
  }

  return <Navigate to={buildTasksPageUrlWithTask(task.id)} replace />
}
