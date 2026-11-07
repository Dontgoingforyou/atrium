import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router'

import { listTrashDocuments, purgePortalDocument, restorePortalDocument } from '../api/documents/documentsApi'
import { PORTAL_NAVIGATION_TREE_QUERY_KEY } from '../api/queryKeys'
import { UserChipBySub } from '../components/ui/UserChip'
import { useDelayedActionContext } from '../hooks/useDelayedActionContext'
import { useNotifyToast } from '../hooks/useNotifyToast'
import { useScheduleDeleteWithUndo } from '../hooks/useScheduleDeleteWithUndo'
import { useAuthStore } from '../store/authStore'
import { DOCUMENT_TRASH_TTL_DAYS } from '../constants/documentTrash'
import { DOCUMENT_TRASH_QUERY_KEY } from '../utils/documents/documentTrashQuery'
import { userFacingMessageFromUnknown } from '../utils/apiUserMessage'
import { invalidatePortalSearchQueries } from '@/utils/search/invalidatePortalSearch'
import { daysUntil, removeTrashItem, type TrashPageData } from '../utils/documents/trashPageHelpers'
import styles from '@/styles/modules/trash/TrashPage.module.css'

export function TrashPage() {
  const qc = useQueryClient()
  const notify = useNotifyToast()
  const isPortalAdmin = useAuthStore((s) => s.user?.is_portal_admin ?? false)
  const scheduleDeleteWithUndo = useScheduleDeleteWithUndo()
  const { hideOptimistically, showOptimistically, optimisticallyHiddenIds } = useDelayedActionContext()

  const trashQuery = useQuery({
    queryKey: DOCUMENT_TRASH_QUERY_KEY,
    queryFn: () => listTrashDocuments(),
    refetchOnWindowFocus: false,
  })

  /** Сайдбар и поиск — без повторного refetch списка корзины (он уже обновлён setQueryData). */
  function invalidateRelatedAfterCommit(): void {
    void qc.invalidateQueries({ queryKey: PORTAL_NAVIGATION_TREE_QUERY_KEY })
    invalidatePortalSearchQueries(qc)
  }

  const restoreMut = useMutation({
    mutationFn: (id: string) => restorePortalDocument(id),
    onError: (e) => notify(userFacingMessageFromUnknown(e)),
  })

  const purgeMut = useMutation({
    mutationFn: (id: string) => purgePortalDocument(id),
    onError: (e) => notify(userFacingMessageFromUnknown(e)),
  })

  function scheduleTrashRemoval(id: string, title: string, kind: 'purge' | 'restore') {
    if (optimisticallyHiddenIds.has(id)) return

    const snapshot = qc.getQueryData<TrashPageData>(DOCUMENT_TRASH_QUERY_KEY)
    const message =
      kind === 'purge'
        ? `Документ «${title}» удалён навсегда`
        : `Документ «${title}» восстановлен`

    scheduleDeleteWithUndo({
      message,
      optimistic: () => {
        hideOptimistically(id)
        qc.setQueryData<TrashPageData>(DOCUMENT_TRASH_QUERY_KEY, (prev) => removeTrashItem(prev, id))
      },
      revert: () => {
        if (snapshot !== undefined) {
          qc.setQueryData(DOCUMENT_TRASH_QUERY_KEY, snapshot)
        }
        showOptimistically(id)
      },
      onUndoClick: () => {
        if (snapshot !== undefined) {
          qc.setQueryData(DOCUMENT_TRASH_QUERY_KEY, snapshot)
        }
        showOptimistically(id)
      },
      commit: () => {
        const mutate = kind === 'purge' ? purgeMut.mutate : restoreMut.mutate
        mutate(id, {
          onError: () => {
            if (snapshot !== undefined) {
              qc.setQueryData(DOCUMENT_TRASH_QUERY_KEY, snapshot)
            }
            showOptimistically(id)
          },
          onSuccess: () => {
            // Кэш корзины уже без строки — не refetch, иначе список «прыгает».
            showOptimistically(id)
            invalidateRelatedAfterCommit()
          },
        })
      },
    })
  }

  if (trashQuery.isPending) {
    return <p className="text-muted">Загрузка корзины…</p>
  }
  if (trashQuery.isError) {
    return <p className="text-danger">{userFacingMessageFromUnknown(trashQuery.error)}</p>
  }

  const rows = (trashQuery.data?.items ?? []).filter((row) => !optimisticallyHiddenIds.has(row.id))

  return (
    <div className={styles.page} data-tour="trash-page">
      <div className="page-header">
        <h1 className="page-title">Корзина документов</h1>
      </div>
      <p className={styles.hint} data-tour="trash-hint">
        Удалённые документы хранятся {DOCUMENT_TRASH_TTL_DAYS} дней, затем удаляются безвозвратно фоновой задачей.
        {isPortalAdmin
          ? ' «Восстановить» и «Удалить навсегда» можно отменить в течение 5 секунд (тост «Отменить»).'
          : ' «Восстановить» можно отменить в течение 5 секунд (тост «Отменить»).'}
      </p>
      {rows.length === 0 ? (
        <p className="text-muted" data-tour="trash-list">
          Корзина пуста.
        </p>
      ) : (
        <ul className={styles.list} data-tour="trash-list">
          {rows.map((row, index) => (
            <li key={row.id} className={styles.row}>
              <div className={styles.rowMain}>
                <span className={styles.docTitle}>{row.title}</span>
                {row.deleted_by_sub ? (
                  <UserChipBySub
                    sub={row.deleted_by_sub}
                    labelOverride={row.deleted_by_display_name ?? undefined}
                    className={styles.deletedBy}
                  />
                ) : row.deleted_by_display_name ? (
                  <span className={styles.meta}>{row.deleted_by_display_name}</span>
                ) : null}
                <span className={styles.meta}>
                  Удалён {new Date(row.deleted_at).toLocaleString('ru-RU')}
                </span>
                <span className={styles.countdown}>
                  Осталось дней: {daysUntil(row.auto_purge_at)}
                </span>
              </div>
              <div className={styles.actions}>
                <button
                  type="button"
                  className={styles.btn}
                  onClick={() => scheduleTrashRemoval(row.id, row.title, 'restore')}
                >
                  Восстановить
                </button>
                {isPortalAdmin ? (
                  <button
                    type="button"
                    className={`${styles.btn} ${styles.btnDanger}`}
                    onClick={() => scheduleTrashRemoval(row.id, row.title, 'purge')}
                    {...(index === 0 ? { 'data-tour': 'trash-purge' } : {})}
                  >
                    Удалить навсегда
                  </button>
                ) : null}
              </div>
            </li>
          ))}
        </ul>
      )}
      <p className={styles.footer}>
        <Link to="/">На главную</Link>
      </p>
    </div>
  )
}
