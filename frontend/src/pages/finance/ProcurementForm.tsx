import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import {
  createProcurementRequest,
  listCounterparties,
  patchProcurementRequest,
} from '../../api/finance/financeApi'
import type {
  PortalProcurementRequest,
  ProcurementRequestCreate,
  ProcurementRequestPatch,
  ProcurementStatus,
} from '../../types/finance'
import { PROCUREMENT_STATUS_LABELS } from '../../domain/finance/financeUi'
import { userFacingMessageFromUnknown } from '../../utils/apiUserMessage'
import styles from '@/styles/modules/finance/FinancePage.module.css'
import { counterpartiesForSelect } from './counterpartiesForSelect'
import { FINANCE_LIST_LIMIT, financeQueryKeys } from './financeQueryKeys'

export function ProcurementForm({
  initial,
  onDone,
  onCancel,
}: {
  initial?: PortalProcurementRequest
  onDone: () => void
  onCancel: () => void
}) {
  const [title, setTitle] = useState(initial?.title ?? '')
  const [description, setDescription] = useState(initial?.description ?? '')
  const [counterpartyId, setCounterpartyId] = useState(initial?.counterparty_id ?? '')
  const [amount, setAmount] = useState(initial?.amount ?? '')
  const [currency, setCurrency] = useState(initial?.currency ?? 'RUB')
  const [status, setStatus] = useState<ProcurementStatus>(initial?.status ?? 'draft')
  const [formError, setFormError] = useState('')

  const {
    data: counterpartiesRaw,
    isError: counterpartiesIsError,
    error: counterpartiesError,
  } = useQuery({
    queryKey: financeQueryKeys.counterparties,
    queryFn: () => listCounterparties({ limit: FINANCE_LIST_LIMIT }),
  })
  const counterparties = counterpartiesForSelect(counterpartiesRaw, counterpartyId)

  const createMutation = useMutation({
    mutationFn: (body: ProcurementRequestCreate) => createProcurementRequest(body),
    onSuccess: onDone,
    onError: (err) => setFormError(userFacingMessageFromUnknown(err)),
  })

  const patchMutation = useMutation({
    mutationFn: (body: ProcurementRequestPatch) => patchProcurementRequest(initial!.id, body),
    onSuccess: onDone,
    onError: (err) => setFormError(userFacingMessageFromUnknown(err)),
  })

  const isPending = createMutation.isPending || patchMutation.isPending

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setFormError('')
    if (!title.trim()) {
      setFormError('Название обязательно')
      return
    }
    const body = {
      title: title.trim(),
      description: description.trim() || null,
      counterparty_id: counterpartyId || null,
      amount: amount || null,
      currency,
      status,
    }
    if (initial) {
      patchMutation.mutate(body)
    } else {
      createMutation.mutate(body)
    }
  }

  return (
    <div className={styles.procurementFormCard}>
      <h3 className={styles.procurementFormTitle}>
        {initial ? 'Редактировать заявку' : 'Новая закупочная заявка'}
      </h3>
      <form onSubmit={handleSubmit} className={styles.procurementFormBody}>
        <div>
          <label className="form-label">Название *</label>
          <input
            className="form-input"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            maxLength={512}
            required
          />
        </div>

        <div>
          <label className="form-label">Описание</label>
          <textarea
            className="form-input"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={3}
          />
        </div>

        <div className={styles.procurementFormRow}>
          <div className={styles.procurementFieldCounterparty}>
            <label className="form-label">Контрагент</label>
            <select className="form-input" value={counterpartyId} onChange={(e) => setCounterpartyId(e.target.value)}>
              <option value="">— не выбран —</option>
              {counterparties.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>

          <div className={styles.procurementFieldAmount}>
            <label className="form-label">Сумма</label>
            <input
              className="form-input"
              type="number"
              min="0"
              step="0.01"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
            />
          </div>

          <div className={styles.procurementFieldCurrency}>
            <label className="form-label">Валюта</label>
            <input
              className="form-input"
              value={currency}
              onChange={(e) => setCurrency(e.target.value)}
              maxLength={10}
            />
          </div>
        </div>

        <div>
          <label className="form-label">Статус</label>
          <select
            className="form-input"
            value={status}
            onChange={(e) => setStatus(e.target.value as ProcurementStatus)}
          >
            {(Object.entries(PROCUREMENT_STATUS_LABELS) as [ProcurementStatus, string][]).map(([val, label]) => (
              <option key={val} value={val}>
                {label}
              </option>
            ))}
          </select>
        </div>

        {counterpartiesIsError && (
          <p className="text-danger">{userFacingMessageFromUnknown(counterpartiesError)}</p>
        )}
        {formError && <p className="text-danger">{formError}</p>}

        {initial && (
          <div>
            <label className="form-label">Автор</label>
            <input type="text" value={initial.author_sub} readOnly disabled className="form-input" />
          </div>
        )}

        <div className={styles.actionBar}>
          <button type="submit" className="btn-primary" disabled={isPending}>
            {isPending ? '…' : initial ? 'Сохранить' : 'Создать'}
          </button>
          <button type="button" className="btn-secondary" onClick={onCancel}>
            Отмена
          </button>
        </div>
      </form>
    </div>
  )
}
