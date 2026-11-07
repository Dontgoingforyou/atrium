import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { listInvoices } from '../../api/finance/financeApi'
import type { InvoiceStatus, InvoiceType } from '../../types/finance'
import { INVOICE_STATUS_LABELS, INVOICE_TYPE_LABELS } from '../../domain/finance/financeUi'
import { userFacingMessageFromUnknown } from '../../utils/apiUserMessage'
import styles from '@/styles/modules/finance/FinancePage.module.css'
import { InvoiceForm } from './InvoiceForm'
import { InvoiceRow } from './InvoiceRow'
import { FINANCE_LIST_LIMIT, financeQueryKeys, invalidateFinanceQueries } from './financeQueryKeys'

export function InvoicesTab({
  statusFilter,
  onStatusFilterChange,
}: {
  statusFilter: string
  onStatusFilterChange: (value: string) => void
}) {
  const queryClient = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [typeFilter, setTypeFilter] = useState('')

  const { data: invoices, isPending, isError, error } = useQuery({
    queryKey: financeQueryKeys.invoices({ status: statusFilter, invoiceType: typeFilter }),
    queryFn: () =>
      listInvoices({
        status: statusFilter || undefined,
        invoice_type: typeFilter || undefined,
        limit: FINANCE_LIST_LIMIT,
      }),
  })

  function invalidate() {
    invalidateFinanceQueries(queryClient, financeQueryKeys.invoicesRoot, financeQueryKeys.summary)
  }

  return (
    <div>
      <div className="filter-bar">
        <select
          value={statusFilter}
          onChange={(e) => onStatusFilterChange(e.target.value)}
          className="filter-select"
          aria-label="Статус счёта"
        >
          <option value="">Все статусы</option>
          {(Object.entries(INVOICE_STATUS_LABELS) as [InvoiceStatus, string][]).map(([val, label]) => (
            <option key={val} value={val}>
              {label}
            </option>
          ))}
        </select>
        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          className="filter-select"
          aria-label="Тип счёта"
        >
          <option value="">Все типы</option>
          {(Object.entries(INVOICE_TYPE_LABELS) as [InvoiceType, string][]).map(([val, label]) => (
            <option key={val} value={val}>
              {label}
            </option>
          ))}
        </select>
        <button type="button" className="btn-primary" onClick={() => setShowForm((v) => !v)}>
          {showForm ? 'Отмена' : '+ Счёт / Акт'}
        </button>
      </div>

      {showForm && (
        <InvoiceForm
          onDone={() => {
            setShowForm(false)
            invalidate()
          }}
          onCancel={() => setShowForm(false)}
        />
      )}

      {isPending ? (
        <p className="text-muted">Загрузка…</p>
      ) : isError ? (
        <p className="text-danger">{userFacingMessageFromUnknown(error)}</p>
      ) : !invoices || invoices.length === 0 ? (
        <p className="text-muted">Счетов и актов нет</p>
      ) : (
        <div className={styles.tableWrapper}>
          <table className={styles.table}>
            <thead>
              <tr className={styles.theadRow}>
                <th className={styles.th}>Название</th>
                <th className={styles.th}>Тип</th>
                <th className={styles.th}>Договор</th>
                <th className={styles.th}>Сумма</th>
                <th className={styles.th}>Статус</th>
                <th className={styles.th}>Срок оплаты</th>
                <th className={styles.th}></th>
              </tr>
            </thead>
            <tbody>
              {invoices.map((inv) => (
                <InvoiceRow key={inv.id} invoice={inv} onUpdated={invalidate} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
