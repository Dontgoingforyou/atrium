import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { createPayment, listInvoices } from '../../api/finance/financeApi'
import type { PaymentCategory, PaymentCreate } from '../../types/finance'
import { PAYMENT_CATEGORY_LABELS } from '../../domain/finance/financeUi'
import { userFacingMessageFromUnknown } from '../../utils/apiUserMessage'
import styles from '@/styles/modules/finance/FinancePage.module.css'
import { FINANCE_LIST_LIMIT, financeQueryKeys } from './financeQueryKeys'

export function PaymentForm({ onDone, onCancel }: { onDone: () => void; onCancel: () => void }) {
  const [amount, setAmount] = useState('')
  const [currency, setCurrency] = useState('RUB')
  const [invoiceId, setInvoiceId] = useState('')
  const [paidAt, setPaidAt] = useState(new Date().toISOString().slice(0, 10))
  const [note, setNote] = useState('')
  const [category, setCategory] = useState<PaymentCategory>('contract')
  const [formError, setFormError] = useState('')

  const {
    data: invoices,
    isError: invoicesIsError,
    error: invoicesError,
  } = useQuery({
    queryKey: financeQueryKeys.invoicesRoot,
    queryFn: () => listInvoices({ limit: FINANCE_LIST_LIMIT }),
  })

  const mutation = useMutation({
    mutationFn: (body: PaymentCreate) => createPayment(body),
    onSuccess: onDone,
    onError: (e: unknown) => setFormError(userFacingMessageFromUnknown(e)),
  })

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!amount || Number(amount) <= 0) {
      setFormError('Введите сумму')
      return
    }
    mutation.mutate({
      amount,
      currency,
      invoice_id: invoiceId || null,
      paid_at: paidAt || null,
      note: note.trim() || null,
      payment_category: category,
    })
  }

  return (
    <form onSubmit={handleSubmit} className={`form-panel ${styles.formPanelNarrow}`}>
      <h3 className="form-panel-title">Новый платёж</h3>
      <div className={styles.formRow}>
        <label className="form-label">
          <span className="form-label-text">Сумма *</span>
          <input
            type="number"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            className={`form-input ${styles.inputAmount}`}
            min={0.01}
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
        <label className={`form-label ${styles.formFieldWide}`}>
          <span className="form-label-text">Счёт / Акт</span>
          <select
            value={invoiceId}
            onChange={(e) => setInvoiceId(e.target.value)}
            className="form-input"
          >
            <option value="">— не выбран —</option>
            {(invoices ?? []).map((inv) => (
              <option key={inv.id} value={inv.id}>
                {inv.title}
              </option>
            ))}
          </select>
        </label>
        <label className="form-label">
          <span className="form-label-text">Категория</span>
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value as PaymentCategory)}
            className="filter-select"
          >
            {(Object.entries(PAYMENT_CATEGORY_LABELS) as [PaymentCategory, string][]).map(([val, label]) => (
              <option key={val} value={val}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <label className="form-label">
          <span className="form-label-text">Дата</span>
          <input type="date" value={paidAt} onChange={(e) => setPaidAt(e.target.value)} className="form-input" />
        </label>
        <label className={`form-label ${styles.formFieldMedium}`}>
          <span className="form-label-text">Примечание</span>
          <input
            type="text"
            value={note}
            onChange={(e) => setNote(e.target.value)}
            className="form-input"
            placeholder="Опционально"
          />
        </label>
      </div>
      {invoicesIsError && <p className="form-error">{userFacingMessageFromUnknown(invoicesError)}</p>}
      {formError && <p className="form-error">{formError}</p>}
      <div className={styles.actionBar}>
        <button type="submit" disabled={mutation.isPending} className="btn-primary">
          {mutation.isPending ? 'Сохранение…' : 'Добавить'}
        </button>
        <button type="button" onClick={onCancel}>
          Отмена
        </button>
      </div>
    </form>
  )
}
