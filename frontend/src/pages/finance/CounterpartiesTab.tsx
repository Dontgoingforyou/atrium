import { useMemo, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { listCounterparties } from '../../api/finance/financeApi'
import type { CounterpartyType } from '../../types/finance'
import { COUNTERPARTY_TYPE_LABELS } from '../../domain/finance/financeUi'
import { userFacingMessageFromUnknown } from '../../utils/apiUserMessage'
import { useAuthStore } from '../../store/authStore'
import styles from '@/styles/modules/finance/FinancePage.module.css'
import { CounterpartyForm } from './CounterpartyForm'
import { CounterpartyRow } from './CounterpartyRow'
import { FINANCE_LIST_LIMIT, financeQueryKeys, invalidateFinanceQueries } from './financeQueryKeys'

export function CounterpartiesTab() {
  const queryClient = useQueryClient()
  const isPortalAdmin = useAuthStore((s) => s.user?.is_portal_admin ?? false)
  const [showForm, setShowForm] = useState(false)
  const [typeFilter, setTypeFilter] = useState('')

  const { data: counterparties, isPending, isError, error } = useQuery({
    queryKey: financeQueryKeys.counterparties,
    queryFn: () => listCounterparties({ limit: FINANCE_LIST_LIMIT }),
  })

  const filtered = useMemo(
    () => counterparties?.filter((c) => !typeFilter || c.counterparty_type === typeFilter),
    [counterparties, typeFilter],
  )

  function invalidate() {
    invalidateFinanceQueries(queryClient, financeQueryKeys.counterparties)
  }

  return (
    <div>
      <div className="filter-bar">
        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          className="filter-select"
          aria-label="Тип контрагента"
        >
          <option value="">Все типы</option>
          {(Object.entries(COUNTERPARTY_TYPE_LABELS) as [CounterpartyType, string][]).map(([val, label]) => (
            <option key={val} value={val}>
              {label}
            </option>
          ))}
        </select>
        {isPortalAdmin && (
          <button type="button" className="btn-primary" onClick={() => setShowForm((v) => !v)}>
            {showForm ? 'Отмена' : '+ Контрагент'}
          </button>
        )}
      </div>

      {showForm && isPortalAdmin && (
        <CounterpartyForm
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
      ) : !filtered || filtered.length === 0 ? (
        <p className="text-muted">Контрагентов нет</p>
      ) : (
        <div className={styles.tableWrapper}>
          <table className={styles.table}>
            <thead>
              <tr className={styles.theadRow}>
                <th className={styles.th}>Название</th>
                <th className={styles.th}>Тип</th>
                <th className={styles.th}>ИНН</th>
                <th className={styles.th}>Email</th>
                <th className={styles.th}>Телефон</th>
                <th className={styles.th}>Статус</th>
                <th className={styles.th}></th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((cp) => (
                <CounterpartyRow key={cp.id} counterparty={cp} onUpdated={invalidate} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
