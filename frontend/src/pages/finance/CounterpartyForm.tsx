import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { createCounterparty, patchCounterparty } from '../../api/finance/financeApi'
import type { CounterpartyCreate, CounterpartyPatch, CounterpartyType, PortalCounterparty } from '../../types/finance'
import { COUNTERPARTY_TYPE_LABELS } from '../../domain/finance/financeUi'
import { userFacingMessageFromUnknown } from '../../utils/apiUserMessage'
import styles from '@/styles/modules/finance/FinancePage.module.css'

export function CounterpartyForm({
  initial,
  onDone,
  onCancel,
}: {
  initial?: PortalCounterparty
  onDone: () => void
  onCancel: () => void
}) {
  const [name, setName] = useState(initial?.name ?? '')
  const [inn, setInn] = useState(initial?.inn ?? '')
  const [cpType, setCpType] = useState<CounterpartyType>(initial?.counterparty_type ?? 'vendor')
  const [email, setEmail] = useState(initial?.contact_email ?? '')
  const [phone, setPhone] = useState(initial?.contact_phone ?? '')
  const [note, setNote] = useState(initial?.note ?? '')
  const [isActive, setIsActive] = useState(initial?.is_active ?? true)
  const [formError, setFormError] = useState('')

  const mutation = useMutation({
    mutationFn: (body: CounterpartyCreate | CounterpartyPatch) =>
      initial
        ? patchCounterparty(initial.id, body as CounterpartyPatch)
        : createCounterparty(body as CounterpartyCreate),
    onSuccess: onDone,
    onError: (e: unknown) => setFormError(userFacingMessageFromUnknown(e)),
  })

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!name.trim()) {
      setFormError('Введите название')
      return
    }
    mutation.mutate({
      name: name.trim(),
      inn: inn.trim() || null,
      counterparty_type: cpType,
      contact_email: email.trim() || null,
      contact_phone: phone.trim() || null,
      note: note.trim() || null,
      is_active: isActive,
    })
  }

  return (
    <form onSubmit={handleSubmit} className={`form-panel ${styles.formPanelMedium}`}>
      <h3 className="form-panel-title">{initial ? 'Редактировать контрагента' : 'Новый контрагент'}</h3>
      <div className={styles.formRow}>
        <label className={`form-label ${styles.formFieldWide}`}>
          <span className="form-label-text">Название *</span>
          <input type="text" value={name} onChange={(e) => setName(e.target.value)} className="form-input" />
        </label>
        <label className="form-label">
          <span className="form-label-text">Тип</span>
          <select
            value={cpType}
            onChange={(e) => setCpType(e.target.value as CounterpartyType)}
            className="filter-select"
          >
            {(Object.entries(COUNTERPARTY_TYPE_LABELS) as [CounterpartyType, string][]).map(([val, label]) => (
              <option key={val} value={val}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <label className="form-label">
          <span className="form-label-text">ИНН</span>
          <input
            type="text"
            value={inn}
            onChange={(e) => setInn(e.target.value)}
            className={`form-input ${styles.inputInn}`}
          />
        </label>
        <label className="form-label">
          <span className="form-label-text">Email</span>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className={`form-input ${styles.inputEmail}`}
          />
        </label>
        <label className="form-label">
          <span className="form-label-text">Телефон</span>
          <input
            type="text"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            className={`form-input ${styles.inputPhone}`}
          />
        </label>
        <label className={`form-label ${styles.formFieldWide}`}>
          <span className="form-label-text">Примечание</span>
          <input type="text" value={note} onChange={(e) => setNote(e.target.value)} className="form-input" />
        </label>
        <label className={`form-label ${styles.checkboxField}`}>
          <span className="form-label-text">Активен</span>
          <input type="checkbox" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} />
        </label>
        {initial && (
          <label className={`form-label ${styles.formFieldWide}`}>
            <span className="form-label-text">Создатель</span>
            <input type="text" value={initial.author_sub} readOnly disabled className="form-input" />
          </label>
        )}
      </div>
      {formError && <p className="form-error">{formError}</p>}
      <div className={styles.actionBar}>
        <button type="submit" disabled={mutation.isPending} className="btn-primary">
          {mutation.isPending ? 'Сохранение…' : initial ? 'Сохранить' : 'Создать'}
        </button>
        <button type="button" onClick={onCancel}>
          Отмена
        </button>
      </div>
    </form>
  )
}
