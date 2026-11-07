import type { Dispatch, SetStateAction } from 'react'
import type { MaterialStatus, MaterialType } from '../../types/learning'
import { MATERIAL_STATUS_LABELS, MATERIAL_TYPE_LABELS, type MaterialFormState } from './materialFormUtils'
import styles from '@/styles/modules/learning/LearningPage.module.css'

export function MaterialFormFields({
  form,
  setForm,
}: {
  form: MaterialFormState
  setForm: Dispatch<SetStateAction<MaterialFormState>>
}) {
  return (
    <div className={styles.adminFieldStack}>
      <label className={styles.adminLabel}>
        Заголовок
        <input
          className={styles.adminInput}
          value={form.title}
          onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
          maxLength={512}
        />
      </label>
      <label className={styles.adminLabel}>
        Тип
        <select
          className={styles.adminInput}
          value={form.material_type}
          onChange={(e) => setForm((f) => ({ ...f, material_type: e.target.value as MaterialType }))}
        >
          {(Object.entries(MATERIAL_TYPE_LABELS) as [MaterialType, string][]).map(([val, label]) => (
            <option key={val} value={val}>
              {label}
            </option>
          ))}
        </select>
      </label>
      <label className={styles.adminLabel}>
        Статус
        <select
          className={styles.adminInput}
          value={form.status}
          onChange={(e) => setForm((f) => ({ ...f, status: e.target.value as MaterialStatus }))}
        >
          {(Object.entries(MATERIAL_STATUS_LABELS) as [MaterialStatus, string][]).map(([val, label]) => (
            <option key={val} value={val}>
              {label}
            </option>
          ))}
        </select>
      </label>
      <label className={styles.adminLabel}>
        Текст
        <textarea
          className={styles.adminTextarea}
          value={form.body}
          onChange={(e) => setForm((f) => ({ ...f, body: e.target.value }))}
          rows={8}
        />
      </label>
    </div>
  )
}
