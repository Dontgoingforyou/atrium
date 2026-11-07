import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { isApiConflictError } from '../../api/apiConflict'
import { deleteMaterial, updateMaterial, type LearningMaterialUpdateBody } from '../../api/learning/learningApi'
import { ConfirmDialog } from '../../components/ui/ConfirmDialog'
import { useNotifyToast } from '../../hooks/useNotifyToast'
import type { LearningMaterial } from '../../types/learning'
import { userFacingMessageFromUnknown } from '../../utils/apiUserMessage'
import { invalidatePortalSearchQueries } from '@/utils/search/invalidatePortalSearch'
import styles from '@/styles/modules/learning/LearningPage.module.css'
import {
  emptyMaterialForm,
  MATERIAL_STATUS_LABELS,
  MATERIAL_TYPE_LABELS,
  type MaterialFormState,
} from './materialFormUtils'
import { MaterialFormFields } from './MaterialFormFields'
import { invalidateLearningQueries, learningQueryKeys } from './learningQueryKeys'

export function MaterialDetail({
  material,
  isAdmin,
  onBack,
  onDeleted,
}: {
  material: LearningMaterial
  isAdmin: boolean
  onBack: () => void
  onDeleted: () => void
}) {
  const qc = useQueryClient()
  const notifyToast = useNotifyToast()
  const [editing, setEditing] = useState(false)
  const [pendingDelete, setPendingDelete] = useState(false)
  const [form, setForm] = useState<MaterialFormState>({
    title: material.title,
    body: material.body ?? '',
    material_type: material.material_type,
    status: material.status,
  })
  const [formError, setFormError] = useState<string | null>(null)

  const updateMut = useMutation({
    mutationFn: (body: LearningMaterialUpdateBody) => updateMaterial(material.id, body),
    onSuccess: () => {
      invalidateLearningQueries(qc, learningQueryKeys.materialsRoot)
      invalidatePortalSearchQueries(qc)
      setEditing(false)
      setForm(emptyMaterialForm())
      setFormError(null)
      onBack()
    },
    onError: (e) => {
      const message = userFacingMessageFromUnknown(e)
      setFormError(message)
      if (isApiConflictError(e)) {
        notifyToast(message)
        invalidateLearningQueries(qc, learningQueryKeys.materialsRoot)
      }
    },
  })

  const deleteMut = useMutation({
    mutationFn: () => deleteMaterial(material.id),
    onSuccess: () => {
      invalidateLearningQueries(qc, learningQueryKeys.materialsRoot)
      invalidatePortalSearchQueries(qc)
      setPendingDelete(false)
      onDeleted()
    },
    onError: (e) => notifyToast(userFacingMessageFromUnknown(e), { silent: true }),
  })

  function submitEdit() {
    if (!form.title.trim()) {
      setFormError('Укажите заголовок.')
      return
    }
    setFormError(null)
    updateMut.mutate({
      expected_version: material.version,
      title: form.title.trim(),
      body: form.body.trim() || null,
      material_type: form.material_type,
      status: form.status,
      idp_groups: material.idp_groups,
    })
  }

  if (editing) {
    return (
      <div className={styles.adminForm}>
        <button
          type="button"
          className={styles.backBtn}
          onClick={() => {
            setEditing(false)
            setForm(emptyMaterialForm())
            setFormError(null)
          }}
        >
          ← Отмена
        </button>
        <h3 className={styles.adminFormTitle}>Редактирование материала</h3>
        {formError ? <p className="text-danger">{formError}</p> : null}
        <MaterialFormFields form={form} setForm={setForm} />
        <div className={styles.adminFormActions}>
          <button
            type="button"
            className="btn-primary"
            disabled={updateMut.isPending}
            onClick={() => submitEdit()}
          >
            {updateMut.isPending ? 'Сохранение…' : 'Сохранить'}
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className={styles.materialDetail}>
      <button type="button" className={styles.backBtn} onClick={onBack}>
        ← Назад к списку
      </button>
      <h2 className={styles.detailTitle}>{material.title}</h2>
      <div className={styles.detailMeta}>
        <span className={styles.materialTypeBadge}>
          {MATERIAL_TYPE_LABELS[material.material_type]}
        </span>
        {isAdmin ? (
          <span className={`${styles.materialTypeBadge} ${styles.badgeAfter}`}>
            {MATERIAL_STATUS_LABELS[material.status]}
          </span>
        ) : null}
      </div>
      {material.body ? (
        <div className={styles.materialBody}>{material.body}</div>
      ) : (
        <p className="text-muted">Содержимое материала отсутствует.</p>
      )}
      {isAdmin ? (
        <div className={styles.adminFormActionsRow}>
          <button
            type="button"
            className="btn-secondary"
            onClick={() => {
              setForm({
                title: material.title,
                body: material.body ?? '',
                material_type: material.material_type,
                status: material.status,
              })
              setEditing(true)
              setFormError(null)
            }}
          >
            Редактировать
          </button>
          <button
            type="button"
            className="btn-secondary"
            disabled={deleteMut.isPending}
            onClick={() => setPendingDelete(true)}
          >
            {deleteMut.isPending ? 'Удаление…' : 'Удалить'}
          </button>
        </div>
      ) : null}
      {pendingDelete ? (
        <ConfirmDialog
          open
          title="Удалить материал?"
          message={`Удалить материал «${material.title}»? Действие необратимо.`}
          confirmLabel="Удалить"
          cancelLabel="Отмена"
          destructive
          confirmSound="error"
          disabled={deleteMut.isPending}
          onConfirm={() => deleteMut.mutate()}
          onCancel={() => {
            if (!deleteMut.isPending) setPendingDelete(false)
          }}
        />
      ) : null}
    </div>
  )
}
