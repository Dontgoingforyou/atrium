import { useState } from 'react'
import type { PortalProcurementRequest } from '../../types/finance'
import { PROCUREMENT_STATUS_COLORS, PROCUREMENT_STATUS_LABELS } from '../../domain/finance/financeUi'
import { useAuthStore } from '../../store/authStore'
import styles from '@/styles/modules/finance/FinancePage.module.css'
import { canMutateOwnedFinanceRecord } from './financeAccess'
import { ProcurementForm } from './ProcurementForm'

export function ProcurementRequestRow({
  request,
  onCancel,
  isCancelling,
  onUpdated,
}: {
  request: PortalProcurementRequest
  onCancel: () => void
  isCancelling: boolean
  onUpdated: () => void
}) {
  const user = useAuthStore((s) => s.user)
  const canMutate = canMutateOwnedFinanceRecord(request.author_sub, user)
  const [editing, setEditing] = useState(false)

  if (editing) {
    return (
      <tr>
        <td colSpan={6} className={styles.tdInlineEdit}>
          <ProcurementForm
            initial={request}
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

  const statusColor = PROCUREMENT_STATUS_COLORS[request.status]
  const isCancelled = request.status === 'cancelled'

  return (
    <tr className={styles.tbodyRow}>
      <td className={styles.td}>{request.title}</td>
      <td className={styles.td}>{request.counterparty?.name ?? '—'}</td>
      <td className={styles.td}>
        {request.amount ? `${Number(request.amount).toLocaleString('ru-RU')} ${request.currency}` : '—'}
      </td>
      <td className={styles.td} style={statusColor ? { color: statusColor } : undefined}>
        {PROCUREMENT_STATUS_LABELS[request.status]}
      </td>
      <td className={`${styles.td} ${styles.tdMuted}`}>{new Date(request.created_at).toLocaleDateString('ru-RU')}</td>
      <td className={styles.tdActions}>
        {canMutate && !isCancelled && (
          <>
            <button type="button" className="btn-secondary btn-sm" onClick={() => setEditing(true)}>
              Изменить
            </button>
            <button type="button" className="btn-danger btn-sm" disabled={isCancelling} onClick={onCancel}>
              {isCancelling ? '…' : 'Отменить'}
            </button>
          </>
        )}
      </td>
    </tr>
  )
}
