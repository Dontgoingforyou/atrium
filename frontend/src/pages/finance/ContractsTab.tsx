import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { deleteContract, listContracts } from '../../api/finance/financeApi'
import type { ContractStatus } from '../../types/finance'
import { CONTRACT_STATUS_LABELS } from '../../domain/finance/financeUi'
import { userFacingMessageFromUnknown } from '../../utils/apiUserMessage'
import { useNotifyToast } from '../../hooks/useNotifyToast'
import { ConfirmDialog } from '../../components/ui/ConfirmDialog'
import styles from '@/styles/modules/finance/FinancePage.module.css'
import { ContractForm } from './ContractForm'
import { ContractRow } from './ContractRow'
import { FINANCE_LIST_LIMIT, financeQueryKeys, invalidateFinanceQueries } from './financeQueryKeys'

export function ContractsTab() {
  const queryClient = useQueryClient()
  const notifyToast = useNotifyToast()
  const [showForm, setShowForm] = useState(false)
  const [statusFilter, setStatusFilter] = useState('')
  const [pendingCancel, setPendingCancel] = useState<{ id: string; title: string } | null>(null)

  const { data: contracts, isPending, isError, error } = useQuery({
    queryKey: financeQueryKeys.contracts(statusFilter),
    queryFn: () => listContracts({ status: statusFilter || undefined, limit: FINANCE_LIST_LIMIT }),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteContract(id),
    onSuccess: () => {
      invalidate()
      setPendingCancel(null)
    },
    onError: (e: unknown) => notifyToast(userFacingMessageFromUnknown(e)),
  })

  function invalidate() {
    invalidateFinanceQueries(queryClient, financeQueryKeys.contractsRoot, financeQueryKeys.summary)
  }

  return (
    <div>
      <div className="filter-bar">
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="filter-select"
          aria-label="Статус договора"
        >
          <option value="">Все статусы</option>
          {(Object.entries(CONTRACT_STATUS_LABELS) as [ContractStatus, string][]).map(([val, label]) => (
            <option key={val} value={val}>
              {label}
            </option>
          ))}
        </select>
        <button type="button" className="btn-primary" onClick={() => setShowForm((v) => !v)}>
          {showForm ? 'Отмена' : '+ Договор'}
        </button>
      </div>

      {showForm && (
        <ContractForm
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
      ) : !contracts || contracts.length === 0 ? (
        <p className="text-muted">Договоров нет</p>
      ) : (
        <div className={styles.tableWrapper}>
          <table className={styles.table}>
            <thead>
              <tr className={styles.theadRow}>
                <th className={styles.th}>Название</th>
                <th className={styles.th}>Контрагент</th>
                <th className={styles.th}>Сумма</th>
                <th className={styles.th}>Статус</th>
                <th className={styles.th}>Начало</th>
                <th className={styles.th}>Конец</th>
                <th className={styles.th}></th>
              </tr>
            </thead>
            <tbody>
              {contracts.map((c) => (
                <ContractRow
                  key={c.id}
                  contract={c}
                  onUpdated={invalidate}
                  isDeleting={deleteMutation.isPending && deleteMutation.variables === c.id}
                  onDelete={() => setPendingCancel({ id: c.id, title: c.title })}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}

      {pendingCancel ? (
        <ConfirmDialog
          open
          title="Отменить договор?"
          message={`Договор «${pendingCancel.title}» будет переведён в статус «Отменён».`}
          confirmLabel="Отменить"
          cancelLabel="Закрыть"
          destructive
          disabled={deleteMutation.isPending}
          onConfirm={() => deleteMutation.mutate(pendingCancel.id)}
          onCancel={() => {
            if (!deleteMutation.isPending) setPendingCancel(null)
          }}
        />
      ) : null}
    </div>
  )
}
