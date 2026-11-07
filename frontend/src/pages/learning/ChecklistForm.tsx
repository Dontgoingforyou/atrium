import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { isApiConflictError } from '../../api/apiConflict'
import { createChecklist, deleteChecklist, updateChecklist } from '../../api/learning/learningApi'
import { ConfirmDialog } from '../../components/ui/ConfirmDialog'
import { useNotifyToast } from '../../hooks/useNotifyToast'
import type { Checklist } from '../../types/learning'
import { userFacingMessageFromUnknown } from '../../utils/apiUserMessage'
import styles from '@/styles/modules/learning/LearningPage.module.css'
import { invalidateLearningQueries, learningQueryKeys } from './learningQueryKeys'

export function ChecklistCreateForm({
  onCancel,
  onCreated,
}: {
  onCancel: () => void
  onCreated: () => void
}) {
  const qc = useQueryClient()
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [idpGroup, setIdpGroup] = useState('')
  const [itemLines, setItemLines] = useState<string[]>([''])
  const [err, setErr] = useState<string | null>(null)

  const mut = useMutation({
    mutationFn: () => {
      const items = itemLines.map((t) => t.trim()).filter(Boolean)
      if (items.length === 0) {
        throw new Error('Добавьте хотя бы один пункт чек-листа.')
      }
      return createChecklist({
        title: title.trim(),
        description: description.trim() || null,
        idp_group: idpGroup.trim(),
        items,
      })
    },
    onSuccess: () => {
      invalidateLearningQueries(qc, learningQueryKeys.checklists)
      setErr(null)
      onCreated()
    },
    onError: (e) => setErr(userFacingMessageFromUnknown(e)),
  })

  return (
    <div className={styles.adminForm}>
      <button type="button" className={styles.backBtn} onClick={onCancel}>
        ← Отмена
      </button>
      <h3 className={styles.adminFormTitle}>Новый чек-лист</h3>
      {err ? <p className="text-danger">{err}</p> : null}
      <div className={styles.adminFieldStack}>
        <label className={styles.adminLabel}>
          Заголовок
          <input className={styles.adminInput} value={title} onChange={(e) => setTitle(e.target.value)} />
        </label>
        <label className={styles.adminLabel}>
          Описание
          <textarea
            className={styles.adminTextarea}
            rows={3}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </label>
        <label className={styles.adminLabel}>
          Группа Keycloak
          <input className={styles.adminInput} value={idpGroup} onChange={(e) => setIdpGroup(e.target.value)} />
        </label>
        <div>
          <div className={styles.adminLabel}>Пункты</div>
          {itemLines.map((line, i) => (
            <div key={i} className={styles.checklistItemRow}>
              <input
                value={line}
                onChange={(e) => {
                  const next = [...itemLines]
                  next[i] = e.target.value
                  setItemLines(next)
                }}
                placeholder={`Пункт ${i + 1}`}
              />
              <button
                type="button"
                className="btn-secondary btn-sm"
                aria-label={`Удалить пункт ${i + 1}`}
                onClick={() => setItemLines(itemLines.filter((_, j) => j !== i))}
                disabled={itemLines.length <= 1}
              >
                ✕
              </button>
            </div>
          ))}
          <button type="button" className="btn-secondary btn-sm" onClick={() => setItemLines([...itemLines, ''])}>
            + Пункт
          </button>
        </div>
      </div>
      <div className={styles.adminFormActions}>
        <button
          type="button"
          className="btn-primary"
          disabled={!title.trim() || mut.isPending}
          onClick={() => mut.mutate()}
        >
          {mut.isPending ? 'Создание…' : 'Создать'}
        </button>
      </div>
    </div>
  )
}

export function ChecklistEditForm({
  checklist,
  onCancel,
  onSaved,
}: {
  checklist: Checklist
  onCancel: () => void
  onSaved: () => void
}) {
  const qc = useQueryClient()
  const notifyToast = useNotifyToast()
  const [title, setTitle] = useState(checklist.title)
  const [description, setDescription] = useState(checklist.description ?? '')
  const [idpGroup, setIdpGroup] = useState(checklist.idp_group ?? '')
  const [itemLines, setItemLines] = useState(() => checklist.items.map((i) => i.text))
  const [err, setErr] = useState<string | null>(null)
  const [pendingDelete, setPendingDelete] = useState(false)

  const saveMut = useMutation({
    mutationFn: () => {
      const items = itemLines.map((t) => t.trim()).filter(Boolean)
      if (items.length === 0) {
        throw new Error('Должен остаться хотя бы один непустой пункт.')
      }
      return updateChecklist(checklist.id, {
        expected_version: checklist.version,
        title: title.trim(),
        description: description.trim() || null,
        idp_group: idpGroup.trim(),
        items,
      })
    },
    onSuccess: () => {
      invalidateLearningQueries(
        qc,
        learningQueryKeys.checklists,
        learningQueryKeys.checklistProgress(checklist.id),
      )
      setErr(null)
      onSaved()
    },
    onError: (e) => {
      const message = userFacingMessageFromUnknown(e)
      setErr(message)
      if (isApiConflictError(e)) {
        notifyToast(message)
        invalidateLearningQueries(
          qc,
          learningQueryKeys.checklists,
          learningQueryKeys.checklistProgress(checklist.id),
        )
      }
    },
  })

  const delMut = useMutation({
    mutationFn: () => deleteChecklist(checklist.id),
    onSuccess: () => {
      invalidateLearningQueries(qc, learningQueryKeys.checklists)
      setPendingDelete(false)
      onSaved()
    },
    onError: (e) => {
      setPendingDelete(false)
      notifyToast(userFacingMessageFromUnknown(e), { silent: true })
      setErr(userFacingMessageFromUnknown(e))
    },
  })

  return (
    <div className={styles.adminForm}>
      <button type="button" className={styles.backBtn} onClick={onCancel}>
        ← Назад
      </button>
      <h3 className={styles.adminFormTitle}>Редактирование чек-листа</h3>
      <p className={`text-muted ${styles.adminHint}`}>
        Сохранение пунктов сбрасывает прогресс всех пользователей по этому чек-листу.
      </p>
      {err ? <p className="text-danger">{err}</p> : null}
      <div className={styles.adminFieldStack}>
        <label className={styles.adminLabel}>
          Заголовок
          <input className={styles.adminInput} value={title} onChange={(e) => setTitle(e.target.value)} />
        </label>
        <label className={styles.adminLabel}>
          Описание
          <textarea
            className={styles.adminTextarea}
            rows={3}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </label>
        <label className={styles.adminLabel}>
          Группа Keycloak
          <input className={styles.adminInput} value={idpGroup} onChange={(e) => setIdpGroup(e.target.value)} />
        </label>
        <div>
          <div className={styles.adminLabel}>Пункты (полная замена)</div>
          {itemLines.map((line, i) => (
            <div key={i} className={styles.checklistItemRow}>
              <input
                value={line}
                onChange={(e) => {
                  const next = [...itemLines]
                  next[i] = e.target.value
                  setItemLines(next)
                }}
              />
              <button
                type="button"
                className="btn-secondary btn-sm"
                aria-label={`Удалить пункт ${i + 1}`}
                onClick={() => setItemLines(itemLines.filter((_, j) => j !== i))}
                disabled={itemLines.length <= 1}
              >
                ✕
              </button>
            </div>
          ))}
          <button type="button" className="btn-secondary btn-sm" onClick={() => setItemLines([...itemLines, ''])}>
            + Пункт
          </button>
        </div>
      </div>
      <div className={styles.adminFormActionsRow}>
        <button
          type="button"
          className="btn-primary"
          disabled={!title.trim() || saveMut.isPending}
          onClick={() => saveMut.mutate()}
        >
          {saveMut.isPending ? 'Сохранение…' : 'Сохранить'}
        </button>
        <button
          type="button"
          className="btn-secondary"
          disabled={delMut.isPending}
          onClick={() => setPendingDelete(true)}
        >
          {delMut.isPending ? 'Удаление…' : 'Удалить'}
        </button>
      </div>
      {pendingDelete ? (
        <ConfirmDialog
          open
          title="Удалить чек-лист?"
          message="Удалить чек-лист и весь прогресс пользователей? Действие необратимо."
          confirmLabel="Удалить"
          cancelLabel="Отмена"
          destructive
          confirmSound="error"
          disabled={delMut.isPending}
          onConfirm={() => delMut.mutate()}
          onCancel={() => {
            if (!delMut.isPending) setPendingDelete(false)
          }}
        />
      ) : null}
    </div>
  )
}
