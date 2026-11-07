import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { createContract, listCounterparties, patchContract } from '../../api/finance/financeApi'
import type {
  ContractCreate,
  ContractPatch,
  ContractStatus,
  ContractType,
  PortalContract,
} from '../../types/finance'
import { CONTRACT_STATUS_LABELS, CONTRACT_TYPE_LABELS } from '../../domain/finance/financeUi'
import { userFacingMessageFromUnknown } from '../../utils/apiUserMessage'
import { getUserDisplayLabel } from '../../utils/userLabel'
import { UserPicker } from '../../components/common/UserPicker'
import { useAuthStore } from '../../store/authStore'
import styles from '@/styles/modules/finance/FinancePage.module.css'
import { counterpartiesForSelect } from './counterpartiesForSelect'
import { FINANCE_LIST_LIMIT, financeQueryKeys } from './financeQueryKeys'

export function ContractForm({
  initial,
  onDone,
  onCancel,
}: {
  initial?: PortalContract
  onDone: () => void
  onCancel: () => void
}) {
  const isPortalAdmin = useAuthStore((s) => s.user?.is_portal_admin ?? false)
  const [title, setTitle] = useState(initial?.title ?? '')
  const [contractType, setContractType] = useState<ContractType>(initial?.contract_type ?? 'active')
  const [counterpartyId, setCounterpartyId] = useState(initial?.counterparty_id ?? '')
  const [amount, setAmount] = useState(initial?.amount ?? '')
  const [currency, setCurrency] = useState(initial?.currency ?? 'RUB')
  const [startDate, setStartDate] = useState(initial?.start_date ?? '')
  const [endDate, setEndDate] = useState(initial?.end_date ?? '')
  const [status, setStatus] = useState<ContractStatus>(initial?.status ?? 'draft')
  const [ownerSub, setOwnerSub] = useState(initial?.owner_sub ?? '')
  const [formError, setFormError] = useState('')

  const {
    data: counterpartiesRaw,
    isError: counterpartiesError,
    error: counterpartiesErr,
  } = useQuery({
    queryKey: financeQueryKeys.counterparties,
    queryFn: () => listCounterparties({ limit: FINANCE_LIST_LIMIT }),
  })
  const counterparties = counterpartiesForSelect(counterpartiesRaw, counterpartyId)

  const mutation = useMutation({
    mutationFn: (body: ContractCreate | ContractPatch) =>
      initial ? patchContract(initial.id, body as ContractPatch) : createContract(body as ContractCreate),
    onSuccess: onDone,
    onError: (e: unknown) => setFormError(userFacingMessageFromUnknown(e)),
  })

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!title.trim()) {
      setFormError('Введите название')
      return
    }
    mutation.mutate({
      title: title.trim(),
      contract_type: contractType,
      counterparty_id: counterpartyId || null,
      amount: amount || null,
      currency,
      start_date: startDate || null,
      end_date: endDate || null,
      status,
      owner_sub: isPortalAdmin ? ownerSub.trim() || null : null,
    })
  }

  const authorLabel = initial?.author_profile
    ? getUserDisplayLabel({
        sub: initial.author_profile.sub,
        display_name: initial.author_profile.full_name,
        email: initial.author_profile.email,
        username: initial.author_profile.username,
      })
    : (initial?.author_sub ?? '')

  return (
    <form onSubmit={handleSubmit} className={`form-panel ${styles.formPanelWide}`}>
      <h3 className="form-panel-title">{initial ? 'Редактировать договор' : 'Новый договор'}</h3>
      <div className={styles.formRow}>
        <label className={`form-label ${styles.formFieldWide}`}>
          <span className="form-label-text">Название *</span>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="form-input"
            placeholder="Договор №…"
          />
        </label>
        <label className="form-label">
          <span className="form-label-text">Тип</span>
          <select
            value={contractType}
            onChange={(e) => setContractType(e.target.value as ContractType)}
            className="filter-select"
          >
            {(Object.entries(CONTRACT_TYPE_LABELS) as [ContractType, string][]).map(([val, label]) => (
              <option key={val} value={val}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <label className={`form-label ${styles.formFieldWide}`}>
          <span className="form-label-text">Контрагент</span>
          <select
            value={counterpartyId}
            onChange={(e) => setCounterpartyId(e.target.value)}
            className="form-input"
          >
            <option value="">— не выбран —</option>
            {counterparties.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </label>
        <label className="form-label">
          <span className="form-label-text">Сумма</span>
          <input
            type="number"
            value={amount ?? ''}
            onChange={(e) => setAmount(e.target.value)}
            className={`form-input ${styles.inputAmount}`}
            min={0}
            step="0.01"
          />
        </label>
        <label className="form-label">
          <span className="form-label-text">Валюта</span>
          <input
            type="text"
            value={currency}
            onChange={(e) => setCurrency(e.target.value)}
            className={`form-input ${styles.inputCurrency}`}
            maxLength={10}
          />
        </label>
        <label className="form-label">
          <span className="form-label-text">Статус</span>
          <select value={status} onChange={(e) => setStatus(e.target.value as ContractStatus)} className="filter-select">
            {(Object.entries(CONTRACT_STATUS_LABELS) as [ContractStatus, string][]).map(([val, label]) => (
              <option key={val} value={val}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <label className="form-label">
          <span className="form-label-text">Начало</span>
          <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} className="form-input" />
        </label>
        <label className="form-label">
          <span className="form-label-text">Конец</span>
          <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} className="form-input" />
        </label>
        {isPortalAdmin && (
          <div className={`form-label ${styles.formFieldWide}`}>
            <span className="form-label-text">Владелец</span>
            <UserPicker value={ownerSub} onChange={(sub) => setOwnerSub(sub)} placeholder="Начните вводить имя…" />
          </div>
        )}
        {initial && (
          <label className={`form-label ${styles.formFieldWide}`}>
            <span className="form-label-text">Автор</span>
            <input type="text" value={authorLabel} readOnly disabled className="form-input" />
          </label>
        )}
      </div>
      {counterpartiesError && (
        <p className="form-error">{userFacingMessageFromUnknown(counterpartiesErr)}</p>
      )}
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
