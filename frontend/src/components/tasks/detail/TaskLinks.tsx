import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { createLink, deleteLink, listLinks } from '../../../api/tasks/tasksApi'
import { useNotifyToast } from '../../../hooks/useNotifyToast'
import { useScheduleDeleteWithUndo } from '../../../hooks/useScheduleDeleteWithUndo'
import { taskLinksQueryKey } from '@/pages/tasks/tasksQueryKeys'
import type { TaskLink, TaskLinkCreate } from '../../../types/task'
import { userFacingMessageFromUnknown } from '../../../utils/apiUserMessage'
import { normalizeHttpUrl } from '../../../utils/html/normalizeHttpUrl'
import { safeExternalUrl } from '../../../utils/safeExternalUrl'
import { IconX } from '../../icons/portalIcons'
import detailStyles from '@/styles/modules/tasks/TaskDetailPage.module.css'
import styles from '@/styles/modules/tasks/TaskLinks.module.css'

export function TaskLinks({ taskId, currentUserSub, isPortalAdmin }: {
  taskId: string
  currentUserSub: string
  isPortalAdmin: boolean
}) {
  const queryClient = useQueryClient()
  const scheduleDeleteWithUndo = useScheduleDeleteWithUndo()
  const notify = useNotifyToast()
  const linksQueryKey = taskLinksQueryKey(taskId)
  const [title, setTitle] = useState('')
  const [url, setUrl] = useState('')
  const [formError, setFormError] = useState<string | null>(null)

  const { data: links = [], isLoading, isError } = useQuery({
    queryKey: linksQueryKey,
    queryFn: () => listLinks(taskId),
  })

  const createMutation = useMutation({
    mutationFn: (body: TaskLinkCreate) => createLink(taskId, body),
    onSuccess: () => {
      setTitle('')
      setUrl('')
      setFormError(null)
      void queryClient.invalidateQueries({ queryKey: linksQueryKey })
    },
    onError: (err) => setFormError(userFacingMessageFromUnknown(err)),
  })

  const deleteMutation = useMutation({
    mutationFn: (linkId: string) => deleteLink(taskId, linkId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: linksQueryKey })
    },
    onError: (err) => {
      void queryClient.invalidateQueries({ queryKey: linksQueryKey })
      notify(userFacingMessageFromUnknown(err))
    },
  })

  function scheduleLinkDelete(link: TaskLink) {
    scheduleDeleteWithUndo({
      message: 'Ссылка удалена',
      optimistic: () => {
        queryClient.setQueryData<TaskLink[]>(linksQueryKey, (prev) =>
          prev ? prev.filter((l) => l.id !== link.id) : [],
        )
      },
      revert: () => {
        queryClient.setQueryData<TaskLink[]>(linksQueryKey, (prev) => {
          const list = prev ?? []
          if (list.some((l) => l.id === link.id)) return list
          return [...list, link].sort(
            (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
          )
        })
      },
      commit: () => deleteMutation.mutate(link.id),
    })
  }

  function handleAdd(e: React.FormEvent) {
    e.preventDefault()
    setFormError(null)
    const normalizedUrl = normalizeHttpUrl(url)
    const trimmedTitle = title.trim()
    if (!normalizedUrl) {
      if (url.trim()) setFormError('Укажите корректный адрес (http или https)')
      return
    }
    createMutation.mutate({ title: trimmedTitle || undefined, url: normalizedUrl })
  }

  return (
    <div className={styles.section}>
      {isLoading ? (
        <span className={styles.emptyText}>Загрузка...</span>
      ) : isError ? (
        <span className={detailStyles.panelEmptyState}>Не удалось загрузить ссылки</span>
      ) : links.length === 0 ? (
        <span className={detailStyles.panelEmptyState}>Ссылки не добавлены</span>
      ) : (
        <ul className={styles.linkList}>
          {links.map((link) => {
            const safeHref = safeExternalUrl(link.url)
            return (
            <li key={link.id} className={styles.linkItem}>
              {safeHref ? (
              <a
                href={safeHref}
                target="_blank"
                rel="noopener noreferrer"
                className={styles.linkAnchor}
                title={link.url}
              >
                {link.title || link.url}
              </a>
              ) : (
                <span className={styles.linkAnchor} title={link.url}>
                  {link.title || link.url}
                </span>
              )}
              <span className={styles.linkMeta}>
                {new Date(link.created_at).toLocaleDateString('ru-RU')}
              </span>
              {(link.created_by_sub === currentUserSub || isPortalAdmin) && (
                <button
                  type="button"
                  className={styles.deleteBtn}
                  title="Удалить ссылку"
                  aria-label="Удалить ссылку"
                  disabled={deleteMutation.isPending}
                  onClick={() => scheduleLinkDelete(link)}
                >
                  <IconX />
                </button>
              )}
            </li>
            )
          })}
        </ul>
      )}

      <form className={styles.addForm} onSubmit={handleAdd}>
        <div className={styles.addFormRow}>
          <input
            className="form-input"
            type="text"
            placeholder="Название (необязательно)"
            value={title}
            maxLength={512}
            onChange={(e) => setTitle(e.target.value)}
          />
          <input
            className="form-input"
            type="text"
            placeholder="https://docs.google.com/..."
            value={url}
            maxLength={2048}
            onChange={(e) => setUrl(e.target.value)}
          />
          <button
            type="submit"
            className="btn-primary"
            disabled={createMutation.isPending || !url.trim()}
          >
            Добавить
          </button>
        </div>
        {formError && <span className={styles.errorText}>{formError}</span>}
      </form>
    </div>
  )
}
