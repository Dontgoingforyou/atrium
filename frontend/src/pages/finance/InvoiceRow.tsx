import { useState } from 'react'
import type { PortalInvoice } from '../../types/finance'
import { INVOICE_STATUS_LABELS, INVOICE_TYPE_LABELS } from '../../domain/finance/financeUi'
import { useAuthStore } from '../../store/authStore'
import styles from '@/styles/modules/finance/FinancePage.module.css'
import { canMutateOwnedFinanceRecord } from './financeAccess'
import { InvoiceForm } from './InvoiceForm'

export function InvoiceRow({ invoice, onUpdated }: { invoice: PortalInvoice; onUpdated: () => void }) {
  const user = useAuthStore((s) => s.user)
  const canMutate = canMutateOwnedFinanceRecord(invoice.author_sub, user)
  const [editing, setEditing] = useState(false)

  if (editing) {
    return (
      <tr>
        <td colSpan={7} className={styles.tdInlineEdit}>
          <InvoiceForm
            initial={invoice}
            onDone={() => {
              setEditing(false)
              onUpdated()
            }}
            onCancel={() => setEditing(false)}
          />
        </td>
      </tr>
    )
  }

  const isOverdue = invoice.status === 'overdue'

  return (
    <tr className={styles.tbodyRow}>
      <td className={`${styles.td} ${styles.tdBold}`}>{invoice.title}</td>
      <td className={styles.td}>{INVOICE_TYPE_LABELS[invoice.invoice_type] ?? invoice.invoice_type}</td>
      <td className={`${styles.td} ${styles.tdMuted}`}>{invoice.contract?.title ?? '—'}</td>
      <td className={styles.td}>
        {invoice.amount ? `${Number(invoice.amount).toLocaleString('ru-RU')} ${invoice.currency}` : '—'}
      </td>
      <td className={`${styles.td} ${isOverdue ? styles.statusOverdue : ''}`}>
        {INVOICE_STATUS_LABELS[invoice.status] ?? invoice.status}
      </td>
      <td className={styles.td}>{invoice.due_date ?? '—'}</td>
      <td className={styles.tdActions}>
        {canMutate && (
          <button type="button" onClick={() => setEditing(true)}>
            Изменить
          </button>
        )}
      </td>
    </tr>
  )
}
