import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { getMyProgress, markChecklistItem, startChecklist } from '../../api/learning/learningApi'
import { useNotifyToast } from '../../hooks/useNotifyToast'
import type { Checklist } from '../../types/learning'
import { userFacingMessageFromUnknown } from '../../utils/apiUserMessage'
import styles from '@/styles/modules/learning/LearningPage.module.css'
import { isChecklistProgressAbsentError } from './checklistProgressError'
import { invalidateLearningQueries, learningQueryKeys } from './learningQueryKeys'

export function ChecklistCard({
  checklist,
  isAdmin,
  onEdit,
  onDeleteFromList,
  deleteFromListPending,
}: {
  checklist: Checklist
  isAdmin: boolean
  onEdit: () => void
  onDeleteFromList?: () => void
  deleteFromListPending?: boolean
}) {
  const queryClient = useQueryClient()
  const notifyToast = useNotifyToast()
  const [expanded, setExpanded] = useState(false)
  const progressKey = learningQueryKeys.checklistProgress(checklist.id)

  const {
    data: progress,
    isPending: progressPending,
    isError: progressError,
    error: progressErr,
  } = useQuery({
    queryKey: progressKey,
    queryFn: () => getMyProgress(checklist.id),
    enabled: expanded,
    retry: false,
  })

  const startMutation = useMutation({
    mutationFn: () => startChecklist(checklist.id),
    onSuccess: () => {
      invalidateLearningQueries(queryClient, progressKey)
    },
  })

  const markMutation = useMutation({
    mutationFn: ({ itemId, isDone }: { itemId: string; isDone: boolean }) =>
      markChecklistItem(checklist.id, itemId, isDone),
    onSuccess: (updated) => {
      queryClient.setQueryData(progressKey, updated)
    },
    onError: (e) => notifyToast(userFacingMessageFromUnknown(e)),
  })

  const doneCount = progress?.item_marks.filter((m) => m.is_done).length ?? 0
  const totalItems = checklist.items.length
  const percent = totalItems > 0 ? Math.round((doneCount / totalItems) * 100) : 0
  const progressAbsent = progressError && isChecklistProgressAbsentError(progressErr)

  return (
    <div className={styles.checklistCard}>
      <div className={styles.checklistHeader}>
        <span className={styles.checklistTitle}>{checklist.title}</span>
        {progress?.status === 'completed' && <span className={styles.completedBadge}>✓ Завершён</span>}
        {isAdmin ? (
          <button type="button" className="btn-secondary btn-sm" onClick={onEdit}>
            Админ
          </button>
        ) : null}
        {isAdmin && onDeleteFromList ? (
          <button
            type="button"
            className="btn-secondary btn-sm"
            disabled={deleteFromListPending}
            onClick={onDeleteFromList}
          >
            Удалить
          </button>
        ) : null}
        <button
          type="button"
          className={`btn-secondary btn-sm ${styles.expandBtn}`}
          onClick={() => setExpanded((v) => !v)}
        >
          {expanded ? 'Свернуть' : 'Открыть'}
        </button>
      </div>

      {checklist.description && (
        <p className={`text-muted ${styles.mutedSmall}`}>{checklist.description}</p>
      )}
      {isAdmin && checklist.idp_group ? (
        <p className={`text-muted ${styles.mutedCaption}`}>Группа: {checklist.idp_group}</p>
      ) : null}

      {expanded && (
        <>
          {progressPending ? (
            <p className="text-muted">Загрузка…</p>
          ) : progress ? (
            <>
              <div className={styles.progressBar}>
                <div className={styles.progressFill} style={{ width: `${percent}%` }} />
              </div>
              <div className={styles.progressText}>
                {doneCount} из {totalItems} выполнено ({percent}%)
              </div>
              <div className={styles.checklistItems}>
                {checklist.items.map((item) => {
                  const mark = progress.item_marks.find((m) => m.item_id === item.id)
                  const isDone = mark?.is_done ?? false
                  return (
                    <label key={item.id} className={styles.checklistItem}>
                      <input
                        type="checkbox"
                        checked={isDone}
                        onChange={(e) =>
                          markMutation.mutate({ itemId: item.id, isDone: e.target.checked })
                        }
                        disabled={markMutation.isPending}
                      />
                      <span className={`${styles.checklistItemText} ${isDone ? styles.done : ''}`}>
                        {item.text}
                      </span>
                    </label>
                  )
                })}
              </div>
            </>
          ) : progressAbsent ? (
            <div>
              <p className={`text-muted ${styles.mutedSmall}`}>Вы ещё не начали этот чек-лист.</p>
              <button
                type="button"
                className="btn-primary"
                onClick={() => startMutation.mutate()}
                disabled={startMutation.isPending}
              >
                {startMutation.isPending ? 'Начинаем…' : 'Начать'}
              </button>
              {startMutation.isError && (
                <p className="text-danger">{userFacingMessageFromUnknown(startMutation.error)}</p>
              )}
            </div>
          ) : (
            <p className="text-danger">{userFacingMessageFromUnknown(progressErr)}</p>
          )}
        </>
      )}
    </div>
  )
}
