import { useState } from 'react'
import type { PortalContract } from '../../types/finance'
import { CONTRACT_STATUS_LABELS } from '../../domain/finance/financeUi'
import { useAuthStore } from '../../store/authStore'
import styles from '@/styles/modules/finance/FinancePage.module.css'
import { ContractForm } from './ContractForm'
import { canMutateOwnedFinanceRecord } from './financeAccess'

export function ContractRow({
  contract,
  onDelete,
  isDeleting,
  onUpdated,
}: {
  contract: PortalContract
  onDelete: () => void
  isDeleting: boolean
  onUpdated: () => void
}) {
  const user = useAuthStore((s) => s.user)
  const canMutate = canMutateOwnedFinanceRecord(contract.author_sub, user)
  const [editing, setEditing] = useState(false)

  if (editing) {
    return (
      <tr>
        <td colSpan={7} className={styles.tdInlineEdit}>
          <ContractForm
            initial={contract}
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

  return (
    <tr className={styles.tbodyRow}>
      <td className={`${styles.td} ${styles.tdBold}`}>{contract.title}</td>
      <td className={styles.td}>{contract.counterparty?.name ?? '—'}</td>
      <td className={styles.td}>
        {contract.amount ? `${Number(contract.amount).toLocaleString('ru-RU')} ${contract.currency}` : '—'}
      </td>
      <td className={styles.td}>{CONTRACT_STATUS_LABELS[contract.status] ?? contract.status}</td>
      <td className={styles.td}>{contract.start_date ?? '—'}</td>
      <td className={styles.td}>{contract.end_date ?? '—'}</td>
      <td className={styles.tdActions}>
        {canMutate && (
          <button type="button" onClick={() => setEditing(true)}>
            Изменить
          </button>
        )}
        {canMutate && contract.status !== 'cancelled' && (
          <button type="button" onClick={onDelete} disabled={isDeleting} className={styles.btnDanger}>
            Отменить
          </button>
        )}
      </td>
    </tr>
  )
}
