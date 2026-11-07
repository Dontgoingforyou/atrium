import { useMemo, useState } from 'react'
import { Link } from 'react-router'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { searchPortal } from '../../../api/search/searchApi'
import { getTask, listTasks, patchTaskWithCas } from '../../../api/tasks/tasksApi'
import { isApiConflictError } from '../../../api/apiConflict'
import { PORTAL_TASKS_ROOT_QUERY_KEY } from '@/api/queryKeys'
import { SearchableSinglePicker } from '../../common/SearchableSinglePicker'
import type { SearchablePickerOption } from '../../common/searchablePickerUtils'
import { useDebouncedEffect } from '../../../hooks/useDebouncedEffect'
import { useNotifyToast } from '../../../hooks/useNotifyToast'
import { userFacingMessageFromUnknown } from '../../../utils/apiUserMessage'
import {
  taskLinkCandidatesQueryKey,
  taskLinkCandidatesSearchQueryKey,
  taskRootQueryKey,
  taskSubtasksQueryKey,
} from '@/pages/tasks/tasksQueryKeys'
import type { PortalTask } from '../../../types/task'
import styles from '@/styles/modules/tasks/TaskContextLinksEditor.module.css'

const UNLINKED_OPTION: SearchablePickerOption = { value: '', label: '— не привязан' }

type Scope = 'parent' | 'subtask'

type Props = {
  task: PortalTask
  taskId: string
}

function taskLabel(task: Pick<PortalTask, 'number' | 'title'>): string {
  const title = task.title.trim() || 'Без названия'
  return task.number != null ? `#${task.number} ${title}` : title
}

function mergeOptions(
  rows: SearchablePickerOption[],
  exclude: Set<string>,
  pinned: SearchablePickerOption | null,
  leading: SearchablePickerOption | null,
): SearchablePickerOption[] {
  const seen = new Set<string>()
  const merged: SearchablePickerOption[] = []
  if (leading) {
    merged.push(leading)
    seen.add(leading.value)
  }
  for (const row of rows) {
    if (!row.value || exclude.has(row.value) || seen.has(row.value)) continue
    seen.add(row.value)
    merged.push(row)
  }
  if (pinned?.value && !seen.has(pinned.value) && !exclude.has(pinned.value)) {
    merged.push(pinned)
  }
  return merged
}

function useTaskCandidateSearch(taskId: string, scope: Scope) {
  const [pickerQuery, setPickerQuery] = useState('')
  const [debouncedQuery, setDebouncedQuery] = useState('')

  useDebouncedEffect(() => setDebouncedQuery(pickerQuery.trim()), [pickerQuery], 300)

  const searchQuery = useQuery({
    queryKey: taskLinkCandidatesSearchQueryKey(taskId, scope, debouncedQuery),
    queryFn: () => searchPortal({ q: debouncedQuery, types: ['task'], limit: 50 }),
    enabled: debouncedQuery.length >= 1,
    staleTime: 10_000,
  })

  return {
    setPickerQuery,
    searching: debouncedQuery.length >= 1,
    searchQuery,
  }
}

export function TaskHierarchyLinks({ task, taskId }: Props) {
  const queryClient = useQueryClient()
  const notifyToast = useNotifyToast()
  const serverParentId = task.parent_task_id ?? ''
  const [parentId, setParentId] = useState(serverParentId)
  const [syncedParent, setSyncedParent] = useState(() => ({ taskId, serverParentId }))
  const [formError, setFormError] = useState('')

  if (taskId !== syncedParent.taskId || serverParentId !== syncedParent.serverParentId) {
    setSyncedParent({ taskId, serverParentId })
    setParentId(serverParentId)
  }

  const parentSearch = useTaskCandidateSearch(taskId, 'parent')
  const subtaskSearch = useTaskCandidateSearch(taskId, 'subtask')

  const listQuery = useQuery({
    queryKey: taskLinkCandidatesQueryKey(taskId),
    queryFn: () => listTasks({ limit: 50 }),
    staleTime: 30_000,
  })

  const subtasksQuery = useQuery({
    queryKey: taskSubtasksQueryKey(taskId),
    queryFn: () => listTasks({ parent_task_id: taskId, limit: 200 }),
  })

  const parentTaskQuery = useQuery({
    queryKey: taskRootQueryKey(parentId),
    queryFn: () => getTask(parentId),
    enabled: Boolean(parentId),
    staleTime: 60_000,
  })

  const subtasks = useMemo(() => subtasksQuery.data ?? [], [subtasksQuery.data])
  const subtaskIds = useMemo(() => new Set(subtasks.map((item) => item.id)), [subtasks])

  const listRows = useMemo(
    () => (listQuery.data ?? []).map((item) => ({ value: item.id, label: taskLabel(item) })),
    [listQuery.data],
  )

  function rowsFor(search: ReturnType<typeof useTaskCandidateSearch>): SearchablePickerOption[] {
    if (!search.searching) return listRows
    return (search.searchQuery.data ?? []).map((hit) => ({
      value: hit.entity_id,
      label: hit.title?.trim() || 'Без названия',
    }))
  }

  const pinnedParent: SearchablePickerOption | null = parentId
    ? {
        value: parentId,
        label:
          parentTaskQuery.data?.id === parentId
            ? taskLabel(parentTaskQuery.data)
            : parentTaskQuery.isPending
              ? 'Загрузка…'
              : `задача ${parentId.slice(0, 8)}…`,
      }
    : null

  const parentOptions = mergeOptions(
    rowsFor(parentSearch),
    new Set([taskId, ...subtaskIds]),
    pinnedParent,
    UNLINKED_OPTION,
  )
  const subtaskOptions = mergeOptions(
    rowsFor(subtaskSearch),
    new Set([taskId, serverParentId, ...subtaskIds]),
    null,
    null,
  )

  function invalidateLinkedTasks(ids: Array<string | null | undefined>) {
    const unique = [...new Set(ids.filter((id): id is string => Boolean(id)))]
    for (const id of unique) {
      void queryClient.invalidateQueries({ queryKey: taskRootQueryKey(id) })
    }
    void queryClient.invalidateQueries({ queryKey: PORTAL_TASKS_ROOT_QUERY_KEY })
  }

  const parentSave = useMutation({
    mutationFn: (nextParentId: string) =>
      patchTaskWithCas(taskId, { parent_task_id: nextParentId || null }, task.version),
    onSuccess: (_saved, nextParentId) => {
      setFormError('')
      if (nextParentId) notifyToast('Сохранено')
      invalidateLinkedTasks([taskId, serverParentId, nextParentId])
    },
    onError: (error) => {
      if (isApiConflictError(error)) {
        void queryClient.invalidateQueries({ queryKey: taskRootQueryKey(taskId) })
      }
      setFormError(userFacingMessageFromUnknown(error))
    },
  })

  const childSave = useMutation({
    mutationFn: (child: { id: string; parentTaskId: string | null; version?: number }) =>
      patchTaskWithCas(child.id, { parent_task_id: child.parentTaskId }, child.version),
    onSuccess: (_saved, child) => {
      setFormError('')
      if (child.parentTaskId) notifyToast('Сохранено')
      invalidateLinkedTasks([taskId, child.id])
    },
    onError: (error) => {
      if (isApiConflictError(error)) {
        void queryClient.invalidateQueries({ queryKey: taskSubtasksQueryKey(taskId) })
      }
      setFormError(userFacingMessageFromUnknown(error))
    },
  })

  const parentChanged = parentId !== serverParentId
  useDebouncedEffect(() => {
    if (!parentChanged) return
    parentSave.mutate(parentId)
  }, [parentId, parentChanged], 600)

  const parentLoading =
    (parentSearch.searching && parentSearch.searchQuery.isFetching) ||
    (!parentSearch.searching && listQuery.isPending)
  const subtaskLoading =
    (subtaskSearch.searching && subtaskSearch.searchQuery.isFetching) ||
    (!subtaskSearch.searching && listQuery.isPending)

  return (
    <>
      <div className={styles.row}>
        <label className="form-label">
          <span className="form-label-text">Родительская задача</span>
          <SearchableSinglePicker
            value={parentId}
            onChange={(nextId) => {
              setFormError('')
              setParentId(nextId)
            }}
            options={parentOptions}
            placeholder="Поиск задачи…"
            loading={parentLoading}
            error={parentSearch.searching ? parentSearch.searchQuery.isError : listQuery.isError}
            filterLocally={false}
            onQueryChange={parentSearch.setPickerQuery}
          />
        </label>
      </div>
      <div className={styles.row}>
        <label className="form-label">
          <span className="form-label-text">Подзадача</span>
          <SearchableSinglePicker
            value=""
            onChange={(nextId) => {
              if (!nextId) return
              setFormError('')
              childSave.mutate({ id: nextId, parentTaskId: taskId })
            }}
            options={subtaskOptions}
            placeholder="Найти существующую задачу…"
            loading={subtaskLoading}
            error={subtaskSearch.searching ? subtaskSearch.searchQuery.isError : listQuery.isError}
            filterLocally={false}
            onQueryChange={subtaskSearch.setPickerQuery}
          />
        </label>
        {subtasksQuery.isError ? (
          <p className="form-error" role="alert">
            {userFacingMessageFromUnknown(subtasksQuery.error)}
          </p>
        ) : null}
        {subtasks.length > 0 ? (
          <ul className={styles.subtaskList}>
            {subtasks.map((subtask) => (
              <li key={subtask.id} className={styles.subtaskItem}>
                <Link to={`/tasks/${subtask.id}`} className={styles.subtaskLink}>
                  {taskLabel(subtask)}
                </Link>
                <button
                  type="button"
                  className={styles.unlinkBtn}
                  disabled={childSave.isPending}
                  onClick={() =>
                    childSave.mutate({
                      id: subtask.id,
                      parentTaskId: null,
                      version: subtask.version,
                    })
                  }
                >
                  Снять
                </button>
              </li>
            ))}
          </ul>
        ) : null}
      </div>
      {!formError && (parentSave.isPending || parentChanged) ? (
        <p className={styles.statusHint}>
          {parentSave.isPending ? 'Сохраняем…' : 'Есть несохранённые изменения…'}
        </p>
      ) : null}
      {formError ? <p className="form-error">{formError}</p> : null}
    </>
  )
}
