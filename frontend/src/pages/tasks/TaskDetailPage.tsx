import { useState } from 'react'
import { Link, Navigate, useLocation, useNavigate, useParams } from 'react-router'
import { useQuery } from '@tanstack/react-query'

import { getTask, getTaskByNumber } from '../../api/tasks/tasksApi'
import { jiraBrowseUrl } from '../../utils/jiraBrowseUrl'
import { TaskDetailBody } from './TaskDetailBody'
import { TaskBackButton } from './TaskBackButton'
import { resolveTaskBackNav } from './taskBackNav'
import { buildTaskShortUrl, buildTasksPageUrlWithTask, TASK_ID_FROM_URL_RE } from './tasksPageUrl'
import { taskByNumberQueryKey, taskRootQueryKey } from './tasksQueryKeys'
import styles from '@/styles/modules/tasks/TaskDetailPage.module.css'

function TaskNumberBadge({ number }: { number: number }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = () => {
    const shortPath = buildTaskShortUrl(number)
    const fullUrl = `${window.location.origin}${shortPath}`
    void navigator.clipboard.writeText(fullUrl).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }

  return (
    <button
      type="button"
      className={styles.taskNumberBadge}
      title={copied ? 'Скопировано!' : 'Скопировать короткую ссылку'}
      aria-label={copied ? 'Ссылка скопирована' : 'Скопировать короткую ссылку'}
      onClick={handleCopy}
    >
      {copied ? '✓' : `#${number}`}
    </button>
  )
}

export function TaskDetailPage() {
  const { taskId: rawTaskId } = useParams<{ taskId: string }>()
  const navigate = useNavigate()
  const location = useLocation()
  const backNav = resolveTaskBackNav(location.state)

  const taskId = rawTaskId && TASK_ID_FROM_URL_RE.test(rawTaskId) ? rawTaskId : null

  const shortUrlMatch = rawTaskId && !taskId ? /^task-(\d+)$/.exec(rawTaskId) : null
  const shortUrlNumber = shortUrlMatch ? parseInt(shortUrlMatch[1], 10) : NaN

  const shortUrlQuery = useQuery({
    queryKey: taskByNumberQueryKey(shortUrlNumber),
    queryFn: () => getTaskByNumber(shortUrlNumber),
    enabled: !isNaN(shortUrlNumber),
    staleTime: 60_000,
    retry: false,
  })

  // Тот же ключ, что у useTaskDetailData — заголовок из общего кэша, без второго HTTP.
  const taskTitleQuery = useQuery({
    queryKey: taskRootQueryKey(taskId ?? ''),
    queryFn: () => getTask(taskId!),
    enabled: !!taskId,
    staleTime: 30_000,
  })
  const task = taskTitleQuery.data

  if (!isNaN(shortUrlNumber)) {
    if (shortUrlQuery.isLoading) return <p className="text-muted">Загрузка…</p>
    if (shortUrlQuery.data) return <Navigate to={buildTasksPageUrlWithTask(shortUrlQuery.data.id)} replace />
    return (
      <div>
        <p className="text-danger">Задача #{shortUrlNumber} не найдена.</p>
        <Link to="/tasks">← Вернуться к задачам</Link>
      </div>
    )
  }

  if (!taskId) {
    return (
      <div>
        <p className="text-danger">Некорректный идентификатор задачи.</p>
        <Link to="/tasks">← Вернуться к задачам</Link>
      </div>
    )
  }

  return (
    <div className={styles.page}>
      <div className="page-header">
        <TaskBackButton label={backNav.label} to={backNav.to} state={backNav.state} />
        {task ? (
          <h1 className={`page-title ${styles.pageTitle}`}>
            {task.number != null ? <TaskNumberBadge number={task.number} /> : null}
            {task.title}
            {task.jira_issue_key ? (
              <a
                className={styles.taskNumberBadge}
                href={jiraBrowseUrl(task.jira_issue_key)}
                target="_blank"
                rel="noreferrer"
                title={task.jira_sync_error ? `Jira sync: ${task.jira_sync_error}` : task.jira_issue_key}
              >
                {task.jira_issue_key}
              </a>
            ) : null}
            {task.jira_sync_error ? (
              <span className="text-danger" title={task.jira_sync_error}>
                {' '}
                ⚠ Jira
              </span>
            ) : null}
          </h1>
        ) : null}
      </div>

      <TaskDetailBody
        taskId={taskId}
        layout="page"
        onDelete={() => navigate(backNav.to, { state: backNav.state })}
      />
    </div>
  )
}
