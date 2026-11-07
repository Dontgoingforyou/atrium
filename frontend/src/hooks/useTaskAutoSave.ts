import { useCallback, useMemo } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'

import { isApiConflictError } from '../api/apiConflict'
import { patchTask } from '../api/tasks/tasksApi'
import { PORTAL_TASKS_ROOT_QUERY_KEY } from '../api/queryKeys'
import {
  taskHistoryQueryKey,
  taskRootQueryKey,
} from '../pages/tasks/tasksQueryKeys'
import type { PortalTask, PortalTaskColumn, TaskPatch, TaskPriority } from '../types/task'
import { isEmptyHtml } from '../utils/html/isEmptyHtml'
import { assigneeSubsFromTask } from '../domain/tasks/assigneeSubsFromTask'
import { shouldPlayTaskDoneSuccess } from '../domain/tasks/taskColumns'
import { userFacingMessageFromUnknown } from '../utils/apiUserMessage'
import { playUiSound } from '../utils/sound/uiSounds'
import { invalidatePortalSearchQueries } from '@/utils/search/invalidatePortalSearch'
import { invalidateTagUsages } from '@/utils/tags/invalidateTagUsages'
import { useDebouncedEffect } from './useDebouncedEffect'
import { useNotifyToast } from './useNotifyToast'

export type TaskFormState = {
  title: string
  description: string
  status: string
  priority: TaskPriority
  assigneeSubs: string[]
  dueDate: string
  selectedTagIds: string[]
  documentId: string
}

export function formStateFromTask(task: PortalTask): TaskFormState {
  return {
    title: task.title,
    description: task.description ?? '',
    status: task.status,
    priority: task.priority,
    assigneeSubs: assigneeSubsFromTask(task),
    dueDate: task.due_at ? task.due_at.slice(0, 10) : '',
    selectedTagIds: task.tags.map((t) => t.id),
    documentId: task.document_id ?? '',
  }
}

export function normalizeDescriptionForCompare(html: string): string {
  return isEmptyHtml(html) ? '' : html
}

function sameStringList(a: string[], b: string[]): boolean {
  if (a.length !== b.length) return false
  const sa = [...a].sort()
  const sb = [...b].sort()
  return sa.every((v, i) => v === sb[i])
}

/** Только изменённые относительно сервера поля + expected_version (CAS). */
export function buildPatchBody(
  form: TaskFormState,
  task: PortalTask,
  canEditAssignees: boolean,
): TaskPatch | null {
  if (!form.title.trim()) return null
  const server = formStateFromTask(task)
  const patch: TaskPatch = { expected_version: task.version }

  const title = form.title.trim()
  if (title !== server.title) patch.title = title

  const desc = isEmptyHtml(form.description) ? null : form.description
  const serverDesc = isEmptyHtml(server.description) ? null : server.description
  if (desc !== serverDesc) patch.description = desc

  if (form.status !== server.status) patch.status = form.status
  if (form.priority !== server.priority) patch.priority = form.priority
  if (form.dueDate !== server.dueDate) patch.due_at = form.dueDate || null
  if (form.documentId !== server.documentId) patch.document_id = form.documentId || null

  if (canEditAssignees && !sameStringList(form.assigneeSubs, server.assigneeSubs)) {
    patch.assignee_subs = form.assigneeSubs
  }
  if (!sameStringList(form.selectedTagIds, server.selectedTagIds)) {
    patch.tag_ids = form.selectedTagIds
  }

  const keys = Object.keys(patch).filter((k) => k !== 'expected_version')
  if (keys.length === 0) return null
  return patch
}

export function formEqualsServer(form: TaskFormState, task: PortalTask): boolean {
  const server = formStateFromTask(task)
  if (form.title !== server.title) return false
  if (
    normalizeDescriptionForCompare(form.description) !==
    normalizeDescriptionForCompare(server.description)
  ) {
    return false
  }
  if (form.status !== server.status) return false
  if (form.priority !== server.priority) return false
  if (form.dueDate !== server.dueDate) return false
  if (form.documentId !== server.documentId) return false
  if (!sameStringList(form.assigneeSubs, server.assigneeSubs)) return false
  return sameStringList(form.selectedTagIds, server.selectedTagIds)
}

export function useTaskAutoSave(options: {
  task: PortalTask
  taskId: string
  enabled: boolean
  canEditAssignees: boolean
  form: TaskFormState
  columns: PortalTaskColumn[]
}) {
  const { task, taskId, enabled, canEditAssignees, form, columns } = options
  const queryClient = useQueryClient()
  const notifyToast = useNotifyToast()

  const patchMutation = useMutation({
    mutationFn: (body: TaskPatch) => patchTask(taskId, body),
    onSuccess: (updated) => {
      if (shouldPlayTaskDoneSuccess(task.status, updated.status, columns)) {
        playUiSound('success')
      }
      queryClient.setQueryData(taskRootQueryKey(taskId), updated)
      void queryClient.invalidateQueries({ queryKey: taskHistoryQueryKey(taskId) })
      queryClient.setQueriesData<PortalTask[]>(
        { queryKey: PORTAL_TASKS_ROOT_QUERY_KEY },
        (prev) => (prev ? prev.map((t) => (t.id === taskId ? { ...t, ...updated } : t)) : prev),
      )
      invalidatePortalSearchQueries(queryClient)
      invalidateTagUsages(queryClient)
    },
    onError: (err) => {
      if (isApiConflictError(err)) {
        notifyToast(err.message, { tone: 'error' })
        void queryClient.invalidateQueries({ queryKey: taskRootQueryKey(taskId) })
      }
    },
  })

  const hasChanges = useMemo(() => !formEqualsServer(form, task), [form, task])

  const save = useCallback(() => {
    if (!enabled || !hasChanges) return
    const body = buildPatchBody(form, task, canEditAssignees)
    if (!body) return
    patchMutation.mutate(body)
  }, [enabled, hasChanges, form, task, canEditAssignees, patchMutation])

  useDebouncedEffect(save, [save], 600)

  const saveError = patchMutation.isError
    ? userFacingMessageFromUnknown(patchMutation.error)
    : ''

  return {
    isSaving: patchMutation.isPending,
    hasChanges,
    saveError,
  }
}
