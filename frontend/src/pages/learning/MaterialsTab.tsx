import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  createMaterial,
  deleteMaterial,
  listMaterials,
  type LearningMaterialCreateBody,
} from '../../api/learning/learningApi'
import { ConfirmDialog } from '../../components/ui/ConfirmDialog'
import { useNotifyToast } from '../../hooks/useNotifyToast'
import { useAuthStore } from '../../store/authStore'
import type { LearningMaterial, MaterialType } from '../../types/learning'
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
import { MaterialDetail } from './MaterialDetail'
import {
  LEARNING_LIST_LIMIT,
  invalidateLearningQueries,
  learningQueryKeys,
} from './learningQueryKeys'

export function MaterialsTab() {
  const isPortalAdmin = useAuthStore((s) => s.user?.is_portal_admin ?? false)
  const notifyToast = useNotifyToast()
  const [typeFilter, setTypeFilter] = useState<string>('')
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [selectedMaterial, setSelectedMaterial] = useState<LearningMaterial | null>(null)
  const [creating, setCreating] = useState(false)
  const [form, setForm] = useState<MaterialFormState>(emptyMaterialForm())
  const [formError, setFormError] = useState<string | null>(null)
  const [pendingDelete, setPendingDelete] = useState<{ id: string; title: string } | null>(null)
  const qc = useQueryClient()

  const { data, isPending, isError, error } = useQuery({
    queryKey: learningQueryKeys.materials({ typeFilter, statusFilter, isPortalAdmin }),
    queryFn: () =>
      listMaterials({
        material_type: typeFilter || undefined,
        status: isPortalAdmin && statusFilter ? statusFilter : undefined,
        limit: LEARNING_LIST_LIMIT,
      }),
  })

  const createMut = useMutation({
    mutationFn: (body: LearningMaterialCreateBody) => createMaterial(body),
    onSuccess: () => {
      invalidateLearningQueries(qc, learningQueryKeys.materialsRoot)
      invalidatePortalSearchQueries(qc)
      setCreating(false)
      setForm(emptyMaterialForm())
      setFormError(null)
    },
    onError: (e) => setFormError(userFacingMessageFromUnknown(e)),
  })

  const deleteMut = useMutation({
    mutationFn: (id: string) => deleteMaterial(id),
    onSuccess: (_void, id) => {
      invalidateLearningQueries(qc, learningQueryKeys.materialsRoot)
      invalidatePortalSearchQueries(qc)
      setSelectedMaterial((cur) => (cur?.id === id ? null : cur))
      setPendingDelete(null)
    },
    onError: (e) => notifyToast(userFacingMessageFromUnknown(e), { silent: true }),
  })

  function submitCreate() {
    if (!form.title.trim()) {
      setFormError('Укажите заголовок.')
      return
    }
    setFormError(null)
    createMut.mutate({
      title: form.title.trim(),
      body: form.body.trim() || null,
      material_type: form.material_type,
      status: form.status,
      idp_groups: [],
    })
  }

  if (selectedMaterial) {
    return (
      <MaterialDetail
        material={selectedMaterial}
        isAdmin={isPortalAdmin}
        onBack={() => setSelectedMaterial(null)}
        onDeleted={() => setSelectedMaterial(null)}
      />
    )
  }

  if (creating) {
    return (
      <div className={styles.adminForm}>
        <button
          type="button"
          className={styles.backBtn}
          onClick={() => {
            setCreating(false)
            setForm(emptyMaterialForm())
            setFormError(null)
          }}
        >
          ← Отмена
        </button>
        <h3 className={styles.adminFormTitle}>Новый материал</h3>
        {formError ? <p className="text-danger">{formError}</p> : null}
        <MaterialFormFields form={form} setForm={setForm} />
        <div className={styles.adminFormActions}>
          <button
            type="button"
            className="btn-primary"
            disabled={createMut.isPending}
            onClick={() => submitCreate()}
          >
            {createMut.isPending ? 'Создание…' : 'Создать'}
          </button>
        </div>
      </div>
    )
  }

  return (
    <div>
      {isPortalAdmin ? (
        <div className={styles.adminToolbar}>
          <select
            className="filter-select"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            aria-label="Статус"
          >
            <option value="">Все статусы</option>
            {(Object.keys(MATERIAL_STATUS_LABELS) as (keyof typeof MATERIAL_STATUS_LABELS)[]).map((s) => (
              <option key={s} value={s}>
                {MATERIAL_STATUS_LABELS[s]}
              </option>
            ))}
          </select>
          <button type="button" className="btn-primary btn-sm" onClick={() => setCreating(true)}>
            + Новый материал
          </button>
        </div>
      ) : null}

      <div className="filter-bar">
        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          className="filter-select"
          aria-label="Тип материала"
        >
          <option value="">Все типы</option>
          {(Object.entries(MATERIAL_TYPE_LABELS) as [MaterialType, string][]).map(([val, label]) => (
            <option key={val} value={val}>
              {label}
            </option>
          ))}
        </select>
      </div>

      {isPending ? (
        <p className="text-muted">Загрузка…</p>
      ) : isError ? (
        <p className="text-danger">{userFacingMessageFromUnknown(error)}</p>
      ) : !data || data.length === 0 ? (
        <p className="text-muted">Материалов нет</p>
      ) : (
        <div className={styles.materialGrid}>
          {data.map((material) => (
            <div key={material.id} className={styles.materialCard}>
              <div className={styles.materialCardHeader}>
                <button
                  type="button"
                  className={styles.materialCardOpen}
                  onClick={() => setSelectedMaterial(material)}
                >
                  <span className={styles.materialTitle}>{material.title}</span>
                  <span className={styles.materialTypeBadge}>
                    {MATERIAL_TYPE_LABELS[material.material_type]}
                  </span>
                </button>
                {isPortalAdmin ? (
                  <span className={styles.materialCardActions}>
                    <button
                      type="button"
                      className="btn-secondary btn-sm"
                      onClick={() => setPendingDelete({ id: material.id, title: material.title })}
                      disabled={deleteMut.isPending}
                    >
                      Удалить
                    </button>
                  </span>
                ) : null}
              </div>
              {isPortalAdmin ? (
                <div className={styles.materialAdminMeta}>
                  {MATERIAL_STATUS_LABELS[material.status]}
                  {material.idp_groups.length > 0 ? ` · ${material.idp_groups.join(', ')}` : ' · для всех'}
                </div>
              ) : null}
              {material.body && (
                <button
                  type="button"
                  className={styles.materialCardOpen}
                  onClick={() => setSelectedMaterial(material)}
                >
                  <span className={styles.materialBody}>
                    {material.body.slice(0, 150)}
                    {material.body.length > 150 ? '…' : ''}
                  </span>
                </button>
              )}
            </div>
          ))}
        </div>
      )}

      {pendingDelete ? (
        <ConfirmDialog
          open
          title="Удалить материал?"
          message={`Удалить материал «${pendingDelete.title}»? Действие необратимо.`}
          confirmLabel="Удалить"
          cancelLabel="Отмена"
          destructive
          confirmSound="error"
          disabled={deleteMut.isPending}
          onConfirm={() => deleteMut.mutate(pendingDelete.id)}
          onCancel={() => {
            if (!deleteMut.isPending) setPendingDelete(null)
          }}
        />
      ) : null}
    </div>
  )
}
