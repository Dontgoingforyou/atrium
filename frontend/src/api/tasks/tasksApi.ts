import type {
  PortalTask,
  PortalTaskColumn,
  TaskBoardPref,
  TaskBoardPrefWrite,
  TaskColumnCreate,
  TaskColumnUpdate,
  TaskComment,
  TaskCommentCreate,
  TaskCommentUpdate,
  TaskCreate,
  TaskFile,
  TaskHistoryEntry,
  TaskLink,
  TaskLinkCreate,
  TaskPatch,
  TaskReorder,
} from '../../types/task'
import { parseJsonOrThrowApi } from '../parseResponse'
import { authenticatedFetch } from '../rawClient'
import { createCommentThreadApi } from '../commentThreadApi'
import type { RichMediaRead } from '../richMediaApi'
import { filenameFromContentDisposition, triggerBlobDownload } from '../../utils/downloadBlob'

export async function listTasks(params?: {
  mine_only?: boolean
  /** Один или несколько sub исполнителей (повторяющиеся query assignee_sub). */
  assignee_sub?: string | string[]
  document_id?: string
  chat_id?: string
  status?: string | string[]
  priority?: string | string[]
  tag_id?: string | string[]
  parent_task_id?: string
  overdue_only?: boolean
  done_this_month?: boolean
  no_assignee?: boolean
  kpi_open_only?: boolean
  skip?: number
  limit?: number
}): Promise<PortalTask[]> {
  const qs = new URLSearchParams()
  if (params?.mine_only) qs.set('mine_only', 'true')
  if (params?.assignee_sub) {
    const subs = Array.isArray(params.assignee_sub) ? params.assignee_sub : [params.assignee_sub]
    for (const s of subs) {
      if (s) qs.append('assignee_sub', s)
    }
  }
  if (params?.document_id) qs.set('document_id', params.document_id)
  if (params?.chat_id) qs.set('chat_id', params.chat_id)
  if (params?.status) {
    const statuses = Array.isArray(params.status) ? params.status : [params.status]
    for (const s of statuses) {
      if (s) qs.append('status', s)
    }
  }
  if (params?.priority) {
    const priorities = Array.isArray(params.priority) ? params.priority : [params.priority]
    for (const p of priorities) {
      if (p) qs.append('priority', p)
    }
  }
  if (params?.tag_id) {
    const tagIds = Array.isArray(params.tag_id) ? params.tag_id : [params.tag_id]
    for (const id of tagIds) {
      if (id) qs.append('tag_id', id)
    }
  }
  if (params?.parent_task_id) qs.set('parent_task_id', params.parent_task_id)
  if (params?.overdue_only) qs.set('overdue_only', 'true')
  if (params?.done_this_month) qs.set('done_this_month', 'true')
  if (params?.no_assignee) qs.set('no_assignee', 'true')
  if (params?.kpi_open_only) qs.set('kpi_open_only', 'true')
  if (params?.skip !== undefined) qs.set('skip', String(params.skip))
  if (params?.limit !== undefined) qs.set('limit', String(params.limit))
  const query = qs.toString() ? `?${qs}` : ''
  const res = await authenticatedFetch(`/portal/tasks${query}`)
  return parseJsonOrThrowApi(res)
}

export async function getTask(taskId: string): Promise<PortalTask> {
  const res = await authenticatedFetch(`/portal/tasks/${taskId}`)
  return parseJsonOrThrowApi(res)
}

export async function getTaskByNumber(number: number): Promise<PortalTask> {
  const res = await authenticatedFetch(`/portal/tasks/by-number/${number}`)
  return parseJsonOrThrowApi(res)
}

export async function createTask(body: TaskCreate): Promise<PortalTask> {
  const res = await authenticatedFetch('/portal/tasks', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return parseJsonOrThrowApi(res)
}

export async function patchTask(taskId: string, body: TaskPatch): Promise<PortalTask> {
  const res = await authenticatedFetch(`/portal/tasks/${taskId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return parseJsonOrThrowApi(res)
}

/** PATCH с CAS: если version не передана — читает текущую с сервера. */
export async function patchTaskWithCas(
  taskId: string,
  patch: Omit<TaskPatch, 'expected_version'>,
  expectedVersion?: number,
): Promise<PortalTask> {
  const version = expectedVersion ?? (await getTask(taskId)).version
  return patchTask(taskId, { ...patch, expected_version: version })
}

export async function deleteTask(taskId: string): Promise<void> {
  const res = await authenticatedFetch(`/portal/tasks/${taskId}`, { method: 'DELETE' })
  if (!res.ok) {
    await parseJsonOrThrowApi(res)
  }
}

export async function reorderTask(body: TaskReorder): Promise<PortalTask> {
  const res = await authenticatedFetch('/portal/tasks/reorder', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return parseJsonOrThrowApi(res)
}

export async function getTaskHistory(
  taskId: string,
  params?: { skip?: number; limit?: number },
): Promise<TaskHistoryEntry[]> {
  const qs = new URLSearchParams()
  if (params?.skip !== undefined) qs.set('skip', String(params.skip))
  if (params?.limit !== undefined) qs.set('limit', String(params.limit))
  const query = qs.toString() ? `?${qs}` : ''
  const res = await authenticatedFetch(`/portal/tasks/${taskId}/history${query}`)
  return parseJsonOrThrowApi(res)
}

export async function listComments(taskId: string): Promise<TaskComment[]> {
  return createCommentThreadApi(`/portal/tasks/${taskId}/comments`).list() as Promise<TaskComment[]>
}

export async function createComment(taskId: string, body: TaskCommentCreate): Promise<TaskComment> {
  return createCommentThreadApi(`/portal/tasks/${taskId}/comments`).create({
    body: body.body,
    parent_id: body.parent_id ?? null,
    mentions: body.mentions ?? [],
    media_ids: body.media_ids ?? [],
  }) as Promise<TaskComment>
}

export async function updateComment(
  taskId: string,
  commentId: string,
  body: TaskCommentUpdate,
): Promise<TaskComment> {
  return createCommentThreadApi(`/portal/tasks/${taskId}/comments`).update(
    commentId,
    body,
  ) as Promise<TaskComment>
}

export async function deleteComment(taskId: string, commentId: string): Promise<void> {
  await createCommentThreadApi(`/portal/tasks/${taskId}/comments`).remove(commentId)
}

export async function uploadTaskCommentMedia(taskId: string, file: File): Promise<RichMediaRead> {
  return createCommentThreadApi(`/portal/tasks/${taskId}/comments`).uploadMedia(file)
}

export async function listTaskColumns(): Promise<PortalTaskColumn[]> {
  const res = await authenticatedFetch('/portal/task-columns')
  return parseJsonOrThrowApi(res)
}

export async function getTaskBoardPref(): Promise<TaskBoardPref> {
  const res = await authenticatedFetch('/portal/me/task-board-pref')
  return parseJsonOrThrowApi(res)
}

export async function putTaskBoardPref(body: TaskBoardPrefWrite): Promise<TaskBoardPref> {
  const res = await authenticatedFetch('/portal/me/task-board-pref', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return parseJsonOrThrowApi(res)
}

export async function createTaskColumn(body: TaskColumnCreate): Promise<PortalTaskColumn> {
  const res = await authenticatedFetch('/portal/task-columns', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return parseJsonOrThrowApi(res)
}

export async function updateTaskColumn(id: string, body: TaskColumnUpdate): Promise<PortalTaskColumn> {
  const res = await authenticatedFetch(`/portal/task-columns/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return parseJsonOrThrowApi(res)
}

export async function deleteTaskColumn(id: string): Promise<void> {
  const res = await authenticatedFetch(`/portal/task-columns/${id}`, {
    method: 'DELETE',
  })
  await parseJsonOrThrowApi(res)
}

export async function exportTaskColumnTasks(params: {
  columnId: string
  mine_only?: boolean
  assignee_sub?: string[]
}): Promise<void> {
  const qs = new URLSearchParams()
  if (params.mine_only) qs.set('mine_only', 'true')
  for (const sub of params.assignee_sub ?? []) {
    qs.append('assignee_sub', sub)
  }
  const query = qs.toString() ? `?${qs}` : ''
  const res = await authenticatedFetch(`/portal/task-columns/${params.columnId}/export${query}`)
  if (!res.ok) {
    await parseJsonOrThrowApi(res)
    return
  }
  const blob = await res.blob()
  const filename = filenameFromContentDisposition(
    res.headers.get('Content-Disposition'),
    'tasks_column.txt',
  )
  triggerBlobDownload(blob, filename)
}

export async function listLinks(taskId: string): Promise<TaskLink[]> {
  const res = await authenticatedFetch(`/portal/tasks/${taskId}/links`)
  return parseJsonOrThrowApi(res)
}

export async function createLink(taskId: string, body: TaskLinkCreate): Promise<TaskLink> {
  const res = await authenticatedFetch(`/portal/tasks/${taskId}/links`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return parseJsonOrThrowApi(res)
}

export async function deleteLink(taskId: string, linkId: string): Promise<void> {
  const res = await authenticatedFetch(`/portal/tasks/${taskId}/links/${linkId}`, {
    method: 'DELETE',
  })
  await parseJsonOrThrowApi<void>(res)
}

export async function listFiles(taskId: string): Promise<TaskFile[]> {
  const res = await authenticatedFetch(`/portal/tasks/${taskId}/files`)
  return parseJsonOrThrowApi(res)
}

export async function uploadFile(taskId: string, file: File): Promise<TaskFile> {
  const formData = new FormData()
  formData.append('file', file)
  const res = await authenticatedFetch(`/portal/tasks/${taskId}/files`, {
    method: 'POST',
    body: formData,
  })
  return parseJsonOrThrowApi(res)
}

export async function deleteFile(taskId: string, fileId: string): Promise<void> {
  const res = await authenticatedFetch(`/portal/tasks/${taskId}/files/${fileId}`, {
    method: 'DELETE',
  })
  await parseJsonOrThrowApi<void>(res)
}
