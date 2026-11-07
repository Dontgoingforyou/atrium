import { useMemo, useState, type MouseEvent } from 'react'
import { Link, useNavigate } from 'react-router'
import {
  DndContext,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors,
  type DragEndEvent,
} from '@dnd-kit/core'
import {
  SortableContext,
  arrayMove,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import type { PortalUserShort } from '../../api/usersApi'
import { useSanitizedRichHtml } from '../../hooks/useSanitizedRichHtml'
import { createTask, listTaskColumns, listTasks, patchTaskWithCas, reorderTask } from '../../api/tasks/tasksApi'
import { isApiConflictError } from '../../api/apiConflict'
import { PORTAL_TASK_COLUMNS_QUERY_KEY } from '../../api/queryKeys'
import { PORTAL_TASKS_ROOT_QUERY_KEY, taskSubtasksQueryKey } from './tasksQueryKeys'
import { resolveSubtaskReorderAnchor } from '../../domain/tasks/subtaskReorder'
import { useNotifyToast } from '../../hooks/useNotifyToast'
import type { PortalTask, TaskStatus } from '../../types/task'
import { UserMultiPicker } from '../../components/common/UserMultiPicker'
import { UserAvatar } from '../../components/ui/UserAvatar'
import { buildTaskStatusSelectOptions, getTaskColumnColor, isTaskOverdue, shouldPlayTaskDoneSuccess } from '../../domain/tasks/taskColumns'
import { PRIORITY_LABELS } from '../../domain/tasks/taskUi'
import { jiraBrowseUrl } from '../../utils/jiraBrowseUrl'
import { playUiSound } from '../../utils/sound/uiSounds'
import { userFacingMessageFromUnknown } from '../../utils/apiUserMessage'
import { handleRichTextContainerClick } from '../../utils/html/richTextLinkClick'
import { TaskTagChips } from '../../components/tasks/TaskTagChips'
import type { TaskBackNavState } from './taskBackNav'
import styles from '@/styles/modules/tasks/TaskDetailPage.module.css'

const EMPTY_SUBTASKS: PortalTask[] = []

function stopDndPointer(e: { stopPropagation(): void }) {
  e.stopPropagation()
}

export function SubtasksSection({
  taskId,
  parentTask,
  portalUsers,
  onOpenTaskDetail,
  taskNavState,
}: {
  taskId: string
  parentTask: PortalTask
  portalUsers?: PortalUserShort[] | undefined
  onOpenTaskDetail?: (taskId: string) => void
  /** Сохраняет возврат на канбан/фильтры при переходе в подзадачу. */
  taskNavState?: TaskBackNavState
}) {
  const queryClient = useQueryClient()
  const notifyToast = useNotifyToast()
  const [newTitle, setNewTitle] = useState('')
  const [assigneeSubs, setAssigneeSubs] = useState<string[]>(() => [...parentTask.assignee_subs])
  const [syncedTaskId, setSyncedTaskId] = useState(taskId)
  const [addError, setAddError] = useState('')
  const queryKey = taskSubtasksQueryKey(taskId)

  if (syncedTaskId !== taskId) {
    setSyncedTaskId(taskId)
    setAssigneeSubs([...parentTask.assignee_subs])
  }

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
  )

  const subtasksQuery = useQuery({
    queryKey,
    queryFn: () => listTasks({ parent_task_id: taskId, limit: 200 }),
  })

  const createMutation = useMutation({
    mutationFn: () =>
      createTask({
        title: newTitle.trim(),
        parent_task_id: taskId,
        assignee_subs: assigneeSubs,
        tag_ids: parentTask.tags.length ? parentTask.tags.map((t) => t.id) : undefined,
      }),
    onSuccess: () => {
      playUiSound('success')
      setNewTitle('')
      setAssigneeSubs([...parentTask.assignee_subs])
      setAddError('')
      void queryClient.invalidateQueries({ queryKey })
      void queryClient.invalidateQueries({ queryKey: PORTAL_TASKS_ROOT_QUERY_KEY })
    },
    onError: (e: unknown) => {
      playUiSound('error')
      setAddError(userFacingMessageFromUnknown(e))
    },
  })

  const reorderMutation = useMutation({
    mutationFn: (vars: {
      taskId: string
      status: string
      afterTaskId: string | null
      beforeTaskId: string | null
    }) =>
      reorderTask({
        task_id: vars.taskId,
        status: vars.status,
        after_task_id: vars.afterTaskId,
        before_task_id: vars.beforeTaskId,
      }),
    onMutate: async ({ taskId: draggedId }) => {
      await queryClient.cancelQueries({ queryKey })
      const previous = queryClient.getQueryData<PortalTask[]>(queryKey)
      return { previous, draggedId }
    },
    onError: (e: unknown, _vars, ctx) => {
      if (ctx?.previous) queryClient.setQueryData(queryKey, ctx.previous)
      notifyToast(userFacingMessageFromUnknown(e))
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey })
      void queryClient.invalidateQueries({ queryKey: PORTAL_TASKS_ROOT_QUERY_KEY })
    },
  })

  const subtasks = subtasksQuery.data ?? EMPTY_SUBTASKS
  const sortableIds = useMemo(() => subtasks.map((s) => s.id), [subtasks])

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event
    if (!over || active.id === over.id) return
    const oldIndex = subtasks.findIndex((t) => t.id === active.id)
    const newIndex = subtasks.findIndex((t) => t.id === over.id)
    if (oldIndex < 0 || newIndex < 0) return

    const next = arrayMove(subtasks, oldIndex, newIndex)
    queryClient.setQueryData<PortalTask[]>(queryKey, next)

    const anchor = resolveSubtaskReorderAnchor(next, String(active.id))
    if (!anchor) {
      queryClient.setQueryData(queryKey, subtasks)
      return
    }
    reorderMutation.mutate({
      taskId: String(active.id),
      status: anchor.status,
      afterTaskId: anchor.afterTaskId,
      beforeTaskId: anchor.beforeTaskId,
    })
  }

  return (
    <div>
      <div className={styles.subtaskForm}>
        <input
          type="text"
          className="form-input"
          placeholder="Название подзадачи"
          aria-label="Название подзадачи"
          value={newTitle}
          onChange={(e) => setNewTitle(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && newTitle.trim()) createMutation.mutate()
          }}
        />
        <label className={`form-label ${styles.subtaskAssigneeField}`}>
          <span className="form-label-text">Исполнители</span>
          <UserMultiPicker
            value={assigneeSubs}
            onChange={setAssigneeSubs}
            placeholder="Исполнители подзадачи…"
          />
        </label>
        <button
          type="button"
          className="btn-primary"
          disabled={createMutation.isPending || !newTitle.trim()}
          onClick={() => createMutation.mutate()}
        >
          {createMutation.isPending ? 'Добавление…' : 'Добавить'}
        </button>
      </div>
      {addError ? <p className="form-error">{addError}</p> : null}
      {subtasksQuery.isPending ? (
        <p className="text-muted">Загрузка…</p>
      ) : subtasksQuery.isError ? (
        <p className="text-danger">{userFacingMessageFromUnknown(subtasksQuery.error)}</p>
      ) : subtasks.length === 0 ? (
        <p className={styles.panelEmptyState}>Подзадач нет.</p>
      ) : (
        <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
          <SortableContext items={sortableIds} strategy={verticalListSortingStrategy}>
            <div className={styles.subtaskList}>
              {subtasks.map((s) => (
                <SortableSubtaskCard
                  key={s.id}
                  subtask={s}
                  parentTaskId={taskId}
                  assigneeUser={
                    s.assignee_sub ? portalUsers?.find((u) => u.sub === s.assignee_sub) : undefined
                  }
                  onOpenTaskDetail={onOpenTaskDetail}
                  taskNavState={taskNavState}
                />
              ))}
            </div>
          </SortableContext>
        </DndContext>
      )}
    </div>
  )
}

function SortableSubtaskCard({
  subtask,
  parentTaskId,
  assigneeUser,
  onOpenTaskDetail,
  taskNavState,
}: {
  subtask: PortalTask
  parentTaskId: string
  assigneeUser?: PortalUserShort | undefined
  onOpenTaskDetail?: (taskId: string) => void
  taskNavState?: TaskBackNavState
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: subtask.id,
  })
  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.85 : undefined,
  }

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={styles.subtaskSortableWrap}
      {...attributes}
      {...listeners}
    >
      <SubtaskCard
        subtask={subtask}
        parentTaskId={parentTaskId}
        assigneeUser={assigneeUser}
        onOpenTaskDetail={onOpenTaskDetail}
        taskNavState={taskNavState}
      />
    </div>
  )
}

function SubtaskCard({
  subtask,
  parentTaskId,
  assigneeUser,
  onOpenTaskDetail,
  taskNavState,
}: {
  subtask: PortalTask
  parentTaskId: string
  assigneeUser?: PortalUserShort | undefined
  onOpenTaskDetail?: (taskId: string) => void
  taskNavState?: TaskBackNavState
}) {
  const queryClient = useQueryClient()
  const notifyToast = useNotifyToast()
  const safeDescriptionHtml = useSanitizedRichHtml(subtask.description)

  const columnsQuery = useQuery({
    queryKey: PORTAL_TASK_COLUMNS_QUERY_KEY,
    queryFn: () => listTaskColumns(),
    staleTime: 60_000,
  })
  const columns = columnsQuery.data ?? []
  const statusOptions = buildTaskStatusSelectOptions(columns, subtask.status)

  const patchMutation = useMutation({
    mutationFn: (status: TaskStatus) =>
      patchTaskWithCas(subtask.id, { status }, subtask.version),
    onSuccess: (_data, newStatus) => {
      if (shouldPlayTaskDoneSuccess(subtask.status, newStatus, columns)) {
        playUiSound('success')
      }
      void queryClient.invalidateQueries({ queryKey: taskSubtasksQueryKey(parentTaskId) })
      void queryClient.invalidateQueries({ queryKey: PORTAL_TASKS_ROOT_QUERY_KEY })
    },
    onError: (e: unknown) => {
      if (isApiConflictError(e)) {
        void queryClient.invalidateQueries({ queryKey: taskSubtasksQueryKey(parentTaskId) })
        void queryClient.invalidateQueries({ queryKey: PORTAL_TASKS_ROOT_QUERY_KEY })
      }
      notifyToast(userFacingMessageFromUnknown(e), { tone: 'error' })
    },
  })

  const navigate = useNavigate()
  const isOverdue = isTaskOverdue(subtask, columns)

  function handleCardClick(e: MouseEvent<HTMLDivElement>) {
    const target = e.target
    if (!(target instanceof Element)) return
    if (target.closest('a, button, select, input, textarea, label')) return
    if (e.ctrlKey || e.metaKey || e.shiftKey) {
      window.open(`/tasks/${subtask.id}`, '_blank', 'noopener,noreferrer')
      return
    }
    if (onOpenTaskDetail) {
      onOpenTaskDetail(subtask.id)
      return
    }
    navigate(`/tasks/${subtask.id}`, { state: taskNavState })
  }

  const assigneeLabel =
    assigneeUser?.display_name?.trim() ||
    assigneeUser?.email?.trim() ||
    assigneeUser?.username?.trim() ||
    subtask.assignee_sub ||
    ''

  return (
    <div className={styles.subtaskCard} onClick={handleCardClick}>
      <div className={styles.subtaskCardTitleRow}>
        <Link
          to={`/tasks/${subtask.id}`}
          state={taskNavState}
          className={styles.subtaskCardTitle}
          onClick={(e) => {
            if (onOpenTaskDetail && !e.ctrlKey && !e.metaKey && !e.shiftKey) {
              e.preventDefault()
              onOpenTaskDetail(subtask.id)
            }
          }}
        >
          <span className={styles.subtaskCardRefNum}>#{subtask.number ?? '?'}</span>
          {subtask.title}
        </Link>
        {subtask.jira_issue_key ? (
          <a
            href={jiraBrowseUrl(subtask.jira_issue_key)}
            target="_blank"
            rel="noreferrer"
            className={styles.subtaskCardRefNum}
            title={subtask.jira_sync_error ? `Jira sync: ${subtask.jira_sync_error}` : subtask.jira_issue_key}
            onPointerDown={stopDndPointer}
            onClick={stopDndPointer}
          >
            {subtask.jira_issue_key}
          </a>
        ) : null}
        {subtask.assignee_sub ? (
          <UserAvatar
            label={assigneeLabel || subtask.assignee_sub}
            imageUrl={assigneeUser?.avatar_url}
            focalX={assigneeUser?.avatar_focal_x}
            focalY={assigneeUser?.avatar_focal_y}
            size="sm"
            className={styles.subtaskAssigneeAvatar}
            title={assigneeLabel || subtask.assignee_sub}
          />
        ) : null}
      </div>
      <div className={styles.subtaskCardControls}>
        <select
          className={styles.subtaskStatusSelect}
          value={subtask.status}
          disabled={patchMutation.isPending}
          aria-label="Статус подзадачи"
          style={{ borderColor: getTaskColumnColor(subtask.status, columns) }}
          onPointerDown={stopDndPointer}
          onClick={stopDndPointer}
          onChange={(e) => patchMutation.mutate(e.target.value as TaskStatus)}
        >
          {statusOptions.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>
      {subtask.description ? (
        <div
          className={styles.subtaskCardDesc}
          dangerouslySetInnerHTML={{ __html: safeDescriptionHtml }}
          onClick={(e) => handleRichTextContainerClick(e)}
        />
      ) : null}
      <div className={styles.subtaskCardMeta}>
        <span className={styles.subtaskCardPriority}>{PRIORITY_LABELS[subtask.priority]}</span>
        {subtask.due_at ? (
          <span className={isOverdue ? styles.subtaskCardOverdue : styles.subtaskCardDue}>
            до {new Date(subtask.due_at).toLocaleDateString('ru-RU')}
          </span>
        ) : null}
      </div>
      {subtask.tags.length > 0 && (
        <div style={{ marginTop: 6 }}>
          <TaskTagChips tags={subtask.tags} />
        </div>
      )}
    </div>
  )
}
