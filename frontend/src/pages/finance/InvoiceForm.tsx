import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { createInvoice, listContracts, patchInvoice } from '../../api/finance/financeApi'
import type { InvoiceCreate, InvoicePatch, InvoiceStatus, InvoiceType, PortalInvoice } from '../../types/finance'
import { INVOICE_STATUS_LABELS, INVOICE_TYPE_LABELS } from '../../domain/finance/financeUi'
import { userFacingMessageFromUnknown } from '../../utils/apiUserMessage'
import styles from '@/styles/modules/finance/FinancePage.module.css'
import { FINANCE_LIST_LIMIT, financeQueryKeys } from './financeQueryKeys'

export function InvoiceForm({
  initial,
  onDone,
  onCancel,
}: {
  initial?: PortalInvoice
  onDone: () => void
  onCancel: () => void
}) {
  const [title, setTitle] = useState(initial?.title ?? '')
  const [invoiceType, setInvoiceType] = useState<InvoiceType>(initial?.invoice_type ?? 'invoice')
  const [contractId, setContractId] = useState(initial?.contract_id ?? '')
  const [amount, setAmount] = useState(initial?.amount ?? '')
  const [currency, setCurrency] = useState(initial?.currency ?? 'RUB')
  const [issueDate, setIssueDate] = useState(initial?.issue_date ?? '')
  const [dueDate, setDueDate] = useState(initial?.due_date ?? '')
  const [status, setStatus] = useState<InvoiceStatus>(initial?.status ?? 'draft')
  const [formError, setFormError] = useState('')

  const {
    data: contracts,
    isError: contractsIsError,
    error: contractsError,
  } = useQuery({
    queryKey: financeQueryKeys.contractsRoot,
    queryFn: () => listContracts({ limit: FINANCE_LIST_LIMIT }),
  })

  const mutation = useMutation({
    mutationFn: (body: InvoiceCreate | InvoicePatch) =>
      initial ? patchInvoice(initial.id, body as InvoicePatch) : createInvoice(body as InvoiceCreate),
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
      invoice_type: invoiceType,
      contract_id: contractId || null,
      amount: amount || null,
      currency,
      issue_date: issueDate || null,
      due_date: dueDate || null,
      status,
    })
  }

  return (
    <form onSubmit={handleSubmit} className={`form-panel ${styles.formPanelMedium}`}>
      <h3 className="form-panel-title">{initial ? 'Редактировать' : 'Новый счёт / акт'}</h3>
      <div className={styles.formRow}>
        <label className={`form-label ${styles.formFieldWide}`}>
          <span className="form-label-text">Название *</span>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="form-input"
          />
        </label>
        <label className="form-label">
          <span className="form-label-text">Тип</span>
          <select
            value={invoiceType}
            onChange={(e) => setInvoiceType(e.target.value as InvoiceType)}
            className="filter-select"
          >
            {(Object.entries(INVOICE_TYPE_LABELS) as [InvoiceType, string][]).map(([val, label]) => (
              <option key={val} value={val}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <label className={`form-label ${styles.formFieldWide}`}>
          <span className="form-label-text">Договор</span>
          <select
            value={contractId}
            onChange={(e) => setContractId(e.target.value)}
            className="form-input"
          >
            <option value="">— не выбран —</option>
            {(contracts ?? []).map((c) => (
              <option key={c.id} value={c.id}>
                {c.title}
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
          <select value={status} onChange={(e) => setStatus(e.target.value as InvoiceStatus)} className="filter-select">
            {(Object.entries(INVOICE_STATUS_LABELS) as [InvoiceStatus, string][]).map(([val, label]) => (
              <option key={val} value={val}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <label className="form-label">
          <span className="form-label-text">Дата выставления</span>
          <input type="date" value={issueDate} onChange={(e) => setIssueDate(e.target.value)} className="form-input" />
        </label>
        <label className="form-label">
          <span className="form-label-text">Срок оплаты</span>
          <input type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} className="form-input" />
        </label>
        {initial && (
          <label className={`form-label ${styles.formFieldWide}`}>
            <span className="form-label-text">Автор</span>
            <input type="text" value={initial.author_sub} readOnly disabled className="form-input" />
          </label>
        )}
      </div>
      {contractsIsError && <p className="form-error">{userFacingMessageFromUnknown(contractsError)}</p>}
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
