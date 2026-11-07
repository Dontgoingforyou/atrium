import { useEffect, useRef, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { invalidatePortalSearchQueries } from '@/utils/search/invalidatePortalSearch'
import { createTask } from '../../api/tasks/tasksApi'
import type { PortalTask, TaskCreate, TaskPriority } from '../../types/task'
import { PRIORITY_LABELS } from '../../domain/tasks/taskUi'
import type { TourDemoTaskPrefill } from '../../onboarding/ensureTourDemoTask'
import { isEmptyHtml } from '../../utils/html/isEmptyHtml'
import { userFacingMessageFromUnknown } from '../../utils/apiUserMessage'
import { playUiSound } from '../../utils/sound/uiSounds'
import { DayCalendarPicker } from '../../components/common/DayCalendarPicker'
import { UserMultiPicker } from '../../components/common/UserMultiPicker'
import { TagPicker } from '../../components/common/TagPicker'
import { RichTextEditor } from '../../components/tasks/richText/RichTextEditor'
import dayPickerStyles from '@/styles/modules/common/DayCalendarPicker.module.css'
import styles from '@/styles/modules/tasks/TasksPageCreateForm.module.css'

type Props = {
  /** После успешного POST; передаётся созданная задача (для редиректа на карточку). */
  onCreated: (created?: PortalTask) => void
  /** Предзаполненный статус (например, из колонки канбана). */
  initialStatus?: string
  /** Предзаполненные исполнители (текущий пользователь или фильтр команды). */
  initialAssigneeSubs?: string[]
  /** Режим онбординга: предзаполнение без авто-POST. */
  tourDemo?: TourDemoTaskPrefill
}

const PRIORITY_OPTIONS: { value: TaskPriority; label: string }[] = [
  { value: 'low', label: PRIORITY_LABELS.low },
  { value: 'medium', label: PRIORITY_LABELS.medium },
  { value: 'high', label: PRIORITY_LABELS.high },
]

/**
 * Форма создания задачи со всеми полями.
 * Задача создаётся автоматически через 800 мс после ввода названия
 * или немедленно по Enter. Прочие поля включаются в запрос в момент создания.
 */
export function CreateTaskForm({ onCreated, initialStatus, initialAssigneeSubs, tourDemo }: Props) {
  const suppressAutoCreate = Boolean(tourDemo?.suppressAutoCreate)
  const titleInputRef = useRef<HTMLInputElement>(null)
  const [title, setTitle] = useState(tourDemo?.title ?? '')
  const [description, setDescription] = useState(tourDemo?.description ?? '')
  const [assigneeSubs, setAssigneeSubs] = useState<string[]>(
    tourDemo?.assigneeSubs ?? initialAssigneeSubs ?? [],
  )
  const [priority, setPriority] = useState<TaskPriority>(tourDemo?.priority ?? 'medium')
  const [tagIds, setTagIds] = useState<string[]>(tourDemo?.tagIds ?? [])
  const [dueDate, setDueDate] = useState(tourDemo?.dueDate ?? '')
  const [formError, setFormError] = useState('')
  const [createdTaskId, setCreatedTaskId] = useState<string | null>(null)
  const queryClient = useQueryClient()

  // Рефы для актуальных значений без stale closure в таймере
  const latestTitle = useRef(title)
  const latestAssignees = useRef(assigneeSubs)
  const latestDescription = useRef(description)
  const latestPriority = useRef(priority)
  const latestTagIds = useRef(tagIds)
  const latestDueDate = useRef(dueDate)
  const pendingCreate = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => { latestTitle.current = title }, [title])
  useEffect(() => { latestAssignees.current = assigneeSubs }, [assigneeSubs])
  useEffect(() => { latestDescription.current = description }, [description])
  useEffect(() => { latestPriority.current = priority }, [priority])
  useEffect(() => { latestTagIds.current = tagIds }, [tagIds])
  useEffect(() => { latestDueDate.current = dueDate }, [dueDate])

  useEffect(() => {
    if (!suppressAutoCreate) titleInputRef.current?.focus()
    return () => {
      if (pendingCreate.current) clearTimeout(pendingCreate.current)
    }
  }, [suppressAutoCreate])

  const mutation = useMutation({
    mutationFn: (body: TaskCreate) => createTask(body),
    onSuccess: (task) => {
      playUiSound('success')
      setCreatedTaskId(task.id)
      invalidatePortalSearchQueries(queryClient)
      onCreated(task)
    },
    onError: (e: unknown) => {
      playUiSound('error')
      setFormError(userFacingMessageFromUnknown(e))
    },
  })

  function doCreate() {
    if (suppressAutoCreate) return
    if (pendingCreate.current) {
      clearTimeout(pendingCreate.current)
      pendingCreate.current = null
    }
    if (mutation.isPending || createdTaskId) return
    const trimmed = latestTitle.current.trim()
    if (!trimmed) {
      setFormError('Укажите название задачи')
      titleInputRef.current?.focus()
      return
    }
    if (latestAssignees.current.length === 0) {
      setFormError('Необходимо назначить хотя бы одного исполнителя')
      return
    }
    setFormError('')
    const body: TaskCreate = {
      title: trimmed,
      assignee_subs: latestAssignees.current,
      status: initialStatus || undefined,
      priority: latestPriority.current,
    }
    if (!isEmptyHtml(latestDescription.current)) body.description = latestDescription.current
    if (latestTagIds.current.length > 0) body.tag_ids = latestTagIds.current
    if (latestDueDate.current) body.due_at = latestDueDate.current
    mutation.mutate(body)
  }

  function scheduleCreate(newTitle: string) {
    if (suppressAutoCreate) return
    if (pendingCreate.current) clearTimeout(pendingCreate.current)
    if (!newTitle.trim()) return
    pendingCreate.current = setTimeout(doCreate, 800)
  }

  function handleTitleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const val = e.target.value
    setTitle(val)
    setFormError('')
    scheduleCreate(val)
  }

  function handleTitleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter') {
      e.preventDefault()
      doCreate()
    }
  }

  return (
    <form
      className={styles.createTaskForm}
      onSubmit={(e) => e.preventDefault()}
      data-tour="tasks-create-form"
      {...(suppressAutoCreate ? { inert: true } : {})}
    >
      <label className="form-label" data-tour="tasks-create-title">
        <span className="form-label-text">Название *</span>
        <input
          ref={titleInputRef}
          type="text"
          value={title}
          onChange={handleTitleChange}
          onKeyDown={handleTitleKeyDown}
          placeholder="Название задачи — Enter для создания"
          className="form-input"
          disabled={mutation.isPending}
          readOnly={suppressAutoCreate}
        />
      </label>

      <div className="form-label" data-tour="tasks-create-assignees">
        <span className="form-label-text">Исполнители *</span>
        <UserMultiPicker
          value={assigneeSubs}
          onChange={setAssigneeSubs}
          placeholder="Добавить исполнителей…"
        />
      </div>

      <div className={styles.formFields}>
        <label className="form-label" data-tour="tasks-create-priority">
          <span className="form-label-text">Приоритет</span>
          <select
            className={`form-input ${styles.formInputAligned}`}
            value={priority}
            onChange={(e) => setPriority(e.target.value as TaskPriority)}
          >
            {PRIORITY_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </label>

        <div className={`form-label ${styles.dueDateField}`} data-tour="tasks-create-due">
          <span className="form-label-text">Срок выполнения</span>
          <DayCalendarPicker
            label=""
            value={dueDate}
            onChange={setDueDate}
            placeholder="Не выбрано"
            className={`${dayPickerStyles.fixedWidth} ${styles.dueDatePicker}`}
          />
        </div>
      </div>

      <div className="form-label" data-tour="tasks-create-tags">
        <span className="form-label-text">Теги</span>
        <TagPicker selectedIds={tagIds} onChange={setTagIds} />
      </div>

      <div className="form-label" data-tour="tasks-create-description">
        <span className="form-label-text">Описание</span>
        <RichTextEditor
          content={description}
          onChange={setDescription}
          placeholder="Описание задачи…"
          minRows={4}
          autoFocus={false}
          entityType="task"
          entityId={createdTaskId ?? undefined}
          editable={!suppressAutoCreate}
        />
      </div>

      {formError ? <p className="form-error">{formError}</p> : null}
      {mutation.isPending && (
        <p className={styles.createTaskSaving}>Создаём задачу…</p>
      )}
    </form>
  )
}
