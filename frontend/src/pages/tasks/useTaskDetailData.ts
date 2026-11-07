import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useQueries, useQuery } from '@tanstack/react-query'

import { getDocument } from '../../api/documents/documentsApi'
import { listChats } from '../../api/chat/chatApi'
import { PORTAL_CHATS_ALL_QUERY_KEY } from '../../api/queryKeys'
import { usePortalUserDirectory } from '../../hooks/usePortalUserDirectory'
import { getTask, getTaskHistory, listComments, listFiles, listLinks, listTasks } from '../../api/tasks/tasksApi'
import { useNotifyToast } from '../../hooks/useNotifyToast'
import { isUserManagerOrAdmin } from '../../domain/auth/authRoles'
import { useAuthStore } from '../../store/authStore'
import { portalDocumentQueryKey } from '@/utils/documents/documentNavigation'
import type { PortalTask } from '../../types/task'
import {
  taskCommentsQueryKey,
  taskFilesQueryKey,
  taskHistoryPageQueryKey,
  taskLinksQueryKey,
  taskRootQueryKey,
  taskSubtasksQueryKey,
} from './tasksQueryKeys'

type Options = {
  taskId: string
  /** Модалка всегда загружает задачу; страница — только при валидном UUID. */
  enabled?: boolean
}

/**
 * Общие queries и резолверы деталей задачи (страница и модалка).
 */
export function useTaskDetailData({ taskId, enabled = true }: Options) {
  const authUser = useAuthStore((s) => s.user)
  const isPortalAdmin = authUser?.is_portal_admin ?? false
  const isManagerOrAdmin = Boolean(authUser && isUserManagerOrAdmin(authUser))
  const currentUserSub = authUser?.sub ?? ''
  const notifyToast = useNotifyToast()
  const syncErrorToasted = useRef<string | null>(null)

  const taskQuery = useQuery({
    queryKey: taskRootQueryKey(taskId),
    queryFn: () => getTask(taskId),
    enabled,
    staleTime: 30_000,
  })

  useEffect(() => {
    const err = taskQuery.data?.jira_sync_error
    if (!err) return
    const key = `${taskId}:${err}`
    if (syncErrorToasted.current === key) return
    syncErrorToasted.current = key
    notifyToast(`Ошибка синхронизации с Jira: ${err}`)
  }, [taskId, taskQuery.data?.jira_sync_error, notifyToast])

  const [historyOpen, setHistoryOpen] = useState(false)
  const [historyLimit, setHistoryLimit] = useState(100)
  const historyQuery = useQuery({
    queryKey: taskHistoryPageQueryKey(taskId, historyLimit),
    queryFn: () => getTaskHistory(taskId, { limit: historyLimit }),
    enabled: enabled && historyOpen,
    staleTime: 30_000,
  })

  const commentsCountQuery = useQuery({
    queryKey: taskCommentsQueryKey(taskId),
    queryFn: () => listComments(taskId),
    enabled,
  })
  const extLinksCountQuery = useQuery({
    queryKey: taskLinksQueryKey(taskId),
    queryFn: () => listLinks(taskId),
    enabled,
  })
  const filesCountQuery = useQuery({
    queryKey: taskFilesQueryKey(taskId),
    queryFn: () => listFiles(taskId),
    enabled,
  })
  const subtasksCountQuery = useQuery({
    queryKey: taskSubtasksQueryKey(taskId),
    queryFn: () => listTasks({ parent_task_id: taskId, limit: 200 }),
    enabled,
  })

  const usersDirectory = usePortalUserDirectory({ enabled })

  const chatsQuery = useQuery({
    queryKey: PORTAL_CHATS_ALL_QUERY_KEY,
    queryFn: () => listChats({ limit: 500 }),
    enabled,
  })

  const task: PortalTask | undefined = taskQuery.data
  const documentId = task?.document_id ?? null

  const resolveUserSub = usersDirectory.getLabel

  const historyDocumentIds = useMemo(() => {
    const ids = new Set<string>()
    for (const e of historyQuery.data ?? []) {
      for (const [field, ch] of Object.entries(e.diff)) {
        if (field !== 'document_id' || !ch || typeof ch !== 'object') continue
        const o = (ch as { old?: unknown; new?: unknown }).old
        const n = (ch as { old?: unknown; new?: unknown }).new
        if (typeof o === 'string' && o.length > 0) ids.add(o)
        if (typeof n === 'string' && n.length > 0) ids.add(n)
      }
    }
    return [...ids]
  }, [historyQuery.data])

  const historyDocumentQueries = useQueries({
    queries: historyDocumentIds.map((docId) => ({
      queryKey: portalDocumentQueryKey(docId),
      queryFn: () => getDocument(docId),
      staleTime: 60_000,
      enabled,
    })),
  })

  const documentTitleByHistoryId = useMemo(() => {
    const m = new Map<string, string>()
    historyDocumentIds.forEach((id, i) => {
      const d = historyDocumentQueries[i]?.data
      if (d) m.set(id, d.title)
    })
    return m
  }, [historyDocumentIds, historyDocumentQueries])

  const resolveDocumentTitle = useCallback(
    (id: string) => documentTitleByHistoryId.get(id) ?? `id ${id.slice(0, 8)}…`,
    [documentTitleByHistoryId],
  )

  const resolveChatTitle = useCallback(
    (id: string) => {
      const c = chatsQuery.data?.find((x) => x.id === id)
      return c ? (c.title?.trim() || 'Чат без названия') : `id ${id.slice(0, 8)}…`
    },
    [chatsQuery.data],
  )

  return {
    isPortalAdmin,
    isManagerOrAdmin,
    currentUserSub,
    task,
    taskQuery,
    documentId,
    historyOpen,
    setHistoryOpen,
    historyLimit,
    setHistoryLimit,
    historyQuery,
    commentsCountQuery,
    extLinksCountQuery,
    filesCountQuery,
    subtasksCountQuery,
    portalUsers: usersDirectory.users,
    resolveUserSub,
    resolveDocumentTitle,
    resolveChatTitle,
  }
}
