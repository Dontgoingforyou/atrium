import { useEffect, useId, useMemo, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router'
import { listTaskColumns } from '../../api/tasks/tasksApi'
import { PORTAL_TASK_COLUMNS_QUERY_KEY } from '../../api/queryKeys'
import type { PortalTask, TaskPriority, TaskStatus } from '../../types/task'
import { buildTaskStatusSelectOptions, getTaskColumnColor, isTaskOverdue } from '../../domain/tasks/taskColumns'
import { assigneeSubsFromTask } from '../../domain/tasks/assigneeSubsFromTask'
import { PRIORITY_LABELS } from '../../domain/tasks/taskUi'
import { useSanitizedRichHtml } from '../../hooks/useSanitizedRichHtml'
import { useSearchHighlightQuery } from '../../hooks/useSearchHighlightQuery'
import { useHighlightedSafeHtml } from '../../hooks/useHighlightedSafeHtml'
import { useScrollToSearchHit } from '../../hooks/useScrollToSearchHit'
import { useScheduleTaskDelete } from '../../hooks/useScheduleTaskDelete'
import { handleRichTextContainerClick } from '../../utils/html/richTextLinkClick'
import { SEARCH_HIGHLIGHT_ATTR, plainTextHasHighlight } from '../../utils/search/searchHighlight'
import { DayCalendarPicker } from '../../components/common/DayCalendarPicker'
import { UserMultiPicker } from '../../components/common/UserMultiPicker'
import { UserPicker } from '../../components/common/UserPicker'
import { RichTextEditor } from '../../components/tasks/richText/RichTextEditor'
import { TaskTagChips } from '../../components/tasks/TaskTagChips'
import { TagPicker } from '../../components/common/TagPicker'
import { useTaskAutoSave, type TaskFormState } from '../../hooks/useTaskAutoSave'
import dayPickerStyles from '@/styles/modules/common/DayCalendarPicker.module.css'
import styles from '@/styles/modules/tasks/TaskDetailPage.module.css'
import '@/styles/modules/search/SearchHitMark.module.css'

export function TaskDetailEditor({
  task,
  taskId,
  canDelete,
  canEdit = true,
  canEditAssignees = false,
  onDelete,
  onScheduleDelete,
}: {
  task: PortalTask
  taskId: string
  canDelete: boolean
  canEdit?: boolean
  canEditAssignees?: boolean
  onDelete?: () => void
  onScheduleDelete?: (taskId: string) => void
}) {
  const navigate = useNavigate()
  const [title, setTitle] = useState(task.title)
  const [description, setDescription] = useState(task.description ?? '')
  const [status, setStatus] = useState<TaskStatus>(task.status)
  const serverStatusRef = useRef(task.status)

  useEffect(() => {
    if (task.status === serverStatusRef.current) return
    setStatus((current) =>
      current === serverStatusRef.current ? (task.status as TaskStatus) : current,
    )
    serverStatusRef.current = task.status
  }, [task.status])
  const [priority, setPriority] = useState<TaskPriority>(task.priority)
  const [assigneeSubs, setAssigneeSubs] = useState<string[]>(() => assigneeSubsFromTask(task))
  const [dueDate, setDueDate] = useState(task.due_at ? task.due_at.slice(0, 10) : '')
  const [selectedTagIds, setSelectedTagIds] = useState<string[]>(task.tags.map((t) => t.id))
  const descriptionFieldLabelId = useId()
  const titleInputRef = useRef<HTMLInputElement>(null)
  const descriptionHighlightRef = useRef<HTMLDivElement>(null)
  const safeDescriptionHtml = useSanitizedRichHtml(task.description)
  const highlightQuery = useSearchHighlightQuery()
  const highlightedDescriptionHtml = useHighlightedSafeHtml(safeDescriptionHtml, highlightQuery)
  const titleMatchesHighlight = Boolean(
    highlightQuery && plainTextHasHighlight(task.title, highlightQuery),
  )
  const descriptionHasSearchHit = Boolean(
    highlightQuery &&
      task.description &&
      highlightedDescriptionHtml.includes(SEARCH_HIGHLIGHT_ATTR),
  )
  useScrollToSearchHit(
    descriptionHighlightRef,
    highlightQuery,
    descriptionHasSearchHit,
  )

  useEffect(() => {
    if (!canEdit) return
    titleInputRef.current?.focus({ preventScroll: true })
    if (task.title === 'Новая задача') {
      titleInputRef.current?.select()
    }
  }, [taskId, canEdit, task.title])

  const columnsQuery = useQuery({
    queryKey: PORTAL_TASK_COLUMNS_QUERY_KEY,
    queryFn: () => listTaskColumns(),
    staleTime: 60_000,
  })

  const statusOptions = useMemo(
    () => buildTaskStatusSelectOptions(columnsQuery.data ?? [], status),
    [columnsQuery.data, status],
  )

  const columns = columnsQuery.data ?? []
  const statusBorderColor = getTaskColumnColor(status, columns)
  const isOverdue = isTaskOverdue({ status, due_at: dueDate || null }, columns)

  const form: TaskFormState = useMemo(
    () => ({
      title,
      description,
      status,
      priority,
      assigneeSubs,
      dueDate,
      selectedTagIds,
      documentId: task.document_id ?? '',
    }),
    [title, description, status, priority, assigneeSubs, dueDate, selectedTagIds, task.document_id],
  )

  const { isSaving, hasChanges, saveError } = useTaskAutoSave({
    task,
    taskId,
    enabled: canEdit,
    canEditAssignees,
    form,
    columns,
  })

  const { scheduleTaskDelete } = useScheduleTaskDelete()

  const handleDelete = () => {
    if (onScheduleDelete) {
      onScheduleDelete(taskId)
    } else {
      scheduleTaskDelete({ taskId })
    }
    if (onDelete) {
      onDelete()
    } else {
      navigate('/tasks')
    }
  }

  const saveStatusText = isSaving
    ? 'Сохраняем…'
    : hasChanges
      ? 'Есть несохранённые изменения…'
      : 'Сохранено'

  if (!canEdit) {
    return (
      <section className={`${styles.card} ${styles.sectionCard}`}>
        <h2 className={styles.cardTitle}>Поля</h2>
        <p className="text-muted" style={{ fontSize: 'var(--font-size-small)' }}>
          Редактирование недоступно: изменять задачу может автор или исполнитель.
        </p>
        <div className={styles.formStack}>
          <p className={titleMatchesHighlight ? styles.titleSearchHit : undefined}>
            <strong>Название:</strong> {task.title}
          </p>
          {task.tags.length > 0 ? (
            <div>
              <TaskTagChips tags={task.tags} />
            </div>
          ) : null}
          {task.description ? (
            <div
              ref={descriptionHighlightRef}
              className={styles.readOnlyDescription}
              dangerouslySetInnerHTML={{
                __html: highlightedDescriptionHtml,
              }}
              onClick={(e) => handleRichTextContainerClick(e)}
            />
          ) : null}
        </div>
      </section>
    )
  }

  return (
    <section className={`${styles.card} ${styles.sectionCard}`}>
      <h2 className={styles.cardTitle}>Поля</h2>
      <div className={styles.formStack}>
        <label className="form-label">
          <span className="form-label-text">Название</span>
          <input
            ref={titleInputRef}
            type="text"
            className={`form-input${titleMatchesHighlight ? ` ${styles.titleSearchHit}` : ''}`}
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
        </label>
        <div className="form-label">
          <span className="form-label-text">Теги</span>
          <TagPicker selectedIds={selectedTagIds} onChange={setSelectedTagIds} />
        </div>
        <div className="form-label">
          <span className="form-label-text" id={descriptionFieldLabelId}>
            Описание
          </span>
          {highlightQuery && descriptionHasSearchHit ? (
            <div
              ref={descriptionHighlightRef}
              className={styles.readOnlyDescription}
              dangerouslySetInnerHTML={{ __html: highlightedDescriptionHtml }}
              onClick={(e) => handleRichTextContainerClick(e)}
            />
          ) : (
            <RichTextEditor
              content={description}
              onChange={setDescription}
              minRows={4}
              ariaLabelledBy={descriptionFieldLabelId}
              entityType="task"
              entityId={taskId}
              autoFocus={false}
            />
          )}
        </div>
        <div className={styles.row}>
          <label className="form-label">
            <span className="form-label-text">Статус</span>
            <select
              className={`form-input ${styles.formInputAligned}`}
              value={status}
              onChange={(e) => setStatus(e.target.value as TaskStatus)}
              style={{ borderColor: statusBorderColor }}
            >
              {statusOptions.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </label>
          <label className="form-label">
            <span className="form-label-text">Приоритет</span>
            <select
              className={`form-input ${styles.formInputAligned}`}
              value={priority}
              onChange={(e) => setPriority(e.target.value as TaskPriority)}
            >
              {(Object.keys(PRIORITY_LABELS) as TaskPriority[]).map((p) => (
                <option key={p} value={p}>
                  {PRIORITY_LABELS[p]}
                </option>
              ))}
            </select>
          </label>
        </div>
        <div className="form-label">
          <span className="form-label-text">Исполнители</span>
          <UserMultiPicker
            value={assigneeSubs}
            onChange={setAssigneeSubs}
            placeholder={canEditAssignees ? 'Добавить исполнителей…' : 'Не назначены'}
            readOnly={!canEditAssignees}
          />
        </div>
        <div className="form-label">
          <span className="form-label-text">Автор</span>
          <UserPicker
            value={task.creator_sub}
            onChange={() => undefined}
            readOnly
          />
        </div>
        <div className={`form-label ${styles.dueDateField}`}>
          <span className="form-label-text">Срок</span>
          <DayCalendarPicker
            label=""
            value={dueDate}
            onChange={setDueDate}
            placeholder="Не выбрано"
            invalid={isOverdue}
            className={`${dayPickerStyles.fixedWidth} ${styles.dueDatePicker}`}
          />
        </div>
        <p className={`text-muted ${styles.saveStatusLine}`} style={{ fontSize: 'var(--font-size-small)' }} aria-live="polite">
          {saveStatusText}
        </p>
        {saveError ? <p className="form-error">{saveError}</p> : null}
        <div className={styles.actionsRow}>
          {canDelete ? (
            <button
              type="button"
              className={`btn-secondary ${styles.deleteTaskBtn}`}
              disabled={isSaving}
              onClick={handleDelete}
            >
              Удалить задачу
            </button>
          ) : null}
        </div>
      </div>
    </section>
  )
}
