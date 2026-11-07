import { useState } from 'react'
import type { PortalCounterparty } from '../../types/finance'
import { COUNTERPARTY_TYPE_LABELS } from '../../domain/finance/financeUi'
import { useAuthStore } from '../../store/authStore'
import styles from '@/styles/modules/finance/FinancePage.module.css'
import { CounterpartyForm } from './CounterpartyForm'

export function CounterpartyRow({
  counterparty,
  onUpdated,
}: {
  counterparty: PortalCounterparty
  onUpdated: () => void
}) {
  const isPortalAdmin = useAuthStore((s) => s.user?.is_portal_admin ?? false)
  const [editing, setEditing] = useState(false)

  if (editing) {
    return (
      <tr>
        <td colSpan={7} className={styles.tdInlineEdit}>
          <CounterpartyForm
            initial={counterparty}
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
    <tr className={`${styles.tbodyRow} ${counterparty.is_active ? '' : styles.rowInactive}`}>
      <td className={`${styles.td} ${styles.tdBold}`}>{counterparty.name}</td>
      <td className={styles.td}>{COUNTERPARTY_TYPE_LABELS[counterparty.counterparty_type]}</td>
      <td className={`${styles.td} ${styles.tdMuted}`}>{counterparty.inn ?? '—'}</td>
      <td className={styles.td}>{counterparty.contact_email ?? '—'}</td>
      <td className={styles.td}>{counterparty.contact_phone ?? '—'}</td>
      <td className={styles.td}>
        <span className={counterparty.is_active ? styles.statusActive : styles.statusMuted}>
          {counterparty.is_active ? 'Активен' : 'Неактивен'}
        </span>
      </td>
      <td className={styles.tdActions}>
        {isPortalAdmin && (
          <button type="button" onClick={() => setEditing(true)}>
            Изменить
          </button>
        )}
      </td>
    </tr>
  )
}
