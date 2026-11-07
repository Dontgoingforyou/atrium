import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { deleteChecklist, listChecklists } from '../../api/learning/learningApi'
import { ConfirmDialog } from '../../components/ui/ConfirmDialog'
import { useNotifyToast } from '../../hooks/useNotifyToast'
import { useAuthStore } from '../../store/authStore'
import type { Checklist } from '../../types/learning'
import { userFacingMessageFromUnknown } from '../../utils/apiUserMessage'
import styles from '@/styles/modules/learning/LearningPage.module.css'
import { ChecklistCard } from './ChecklistCard'
import { ChecklistCreateForm, ChecklistEditForm } from './ChecklistForm'
import {
  LEARNING_LIST_LIMIT,
  invalidateLearningQueries,
  learningQueryKeys,
} from './learningQueryKeys'

export function ChecklistsTab() {
  const isPortalAdmin = useAuthStore((s) => s.user?.is_portal_admin ?? false)
  const notifyToast = useNotifyToast()
  const qc = useQueryClient()
  const [creating, setCreating] = useState(false)
  const [editing, setEditing] = useState<Checklist | null>(null)
  const [pendingDelete, setPendingDelete] = useState<{ id: string; title: string } | null>(null)

  const listDeleteMut = useMutation({
    mutationFn: (id: string) => deleteChecklist(id),
    onSuccess: () => {
      invalidateLearningQueries(qc, learningQueryKeys.checklists)
      setPendingDelete(null)
    },
    onError: (e) => notifyToast(userFacingMessageFromUnknown(e), { silent: true }),
  })

  const { data, isPending, isError, error } = useQuery({
    queryKey: learningQueryKeys.checklists,
    queryFn: () => listChecklists({ limit: LEARNING_LIST_LIMIT }),
  })

  if (creating) {
    return (
      <ChecklistCreateForm
        onCancel={() => setCreating(false)}
        onCreated={() => setCreating(false)}
      />
    )
  }

  if (editing) {
    return (
      <ChecklistEditForm
        checklist={editing}
        onCancel={() => setEditing(null)}
        onSaved={() => setEditing(null)}
      />
    )
  }

  if (isPending) return <p className="text-muted">Загрузка…</p>
  if (isError) return <p className="text-danger">{userFacingMessageFromUnknown(error)}</p>

  return (
    <div>
      {isPortalAdmin ? (
        <div className={styles.adminToolbar}>
          <button type="button" className="btn-primary btn-sm" onClick={() => setCreating(true)}>
            + Новый чек-лист
          </button>
        </div>
      ) : null}

      {!data || data.length === 0 ? (
        <p className="text-muted">Чек-листов нет</p>
      ) : (
        <div className={styles.checklistList}>
          {data.map((cl) => (
            <ChecklistCard
              key={cl.id}
              checklist={cl}
              isAdmin={isPortalAdmin}
              onEdit={() => setEditing(cl)}
              onDeleteFromList={() => setPendingDelete({ id: cl.id, title: cl.title })}
              deleteFromListPending={listDeleteMut.isPending}
            />
          ))}
        </div>
      )}

      {pendingDelete ? (
        <ConfirmDialog
          open
          title="Удалить чек-лист?"
          message={`Удалить чек-лист «${pendingDelete.title}» и весь прогресс пользователей? Действие необратимо.`}
          confirmLabel="Удалить"
          cancelLabel="Отмена"
          destructive
          confirmSound="error"
          disabled={listDeleteMut.isPending}
          onConfirm={() => listDeleteMut.mutate(pendingDelete.id)}
          onCancel={() => {
            if (!listDeleteMut.isPending) setPendingDelete(null)
          }}
        />
      ) : null}
    </div>
  )
}
