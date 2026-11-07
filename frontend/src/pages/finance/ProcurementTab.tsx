import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { deleteProcurementRequest, getProcurementSummary, listProcurementRequests } from '../../api/finance/financeApi'
import type { ProcurementStatus } from '../../types/finance'
import { PROCUREMENT_STATUS_LABELS } from '../../domain/finance/financeUi'
import { userFacingMessageFromUnknown } from '../../utils/apiUserMessage'
import { useNotifyToast } from '../../hooks/useNotifyToast'
import { ConfirmDialog } from '../../components/ui/ConfirmDialog'
import { useAuthStore } from '../../store/authStore'
import styles from '@/styles/modules/finance/FinancePage.module.css'
import { canCreateProcurementRequest } from './financeAccess'
import { ProcurementForm } from './ProcurementForm'
import { ProcurementRequestRow } from './ProcurementRequestRow'
import { FINANCE_LIST_LIMIT, financeQueryKeys, invalidateFinanceQueries } from './financeQueryKeys'

export function ProcurementTab() {
  const queryClient = useQueryClient()
  const notifyToast = useNotifyToast()
  const user = useAuthStore((s) => s.user)
  const canCreate = canCreateProcurementRequest(user)
  const [showForm, setShowForm] = useState(false)
  const [statusFilter, setStatusFilter] = useState('')
  const [pendingCancel, setPendingCancel] = useState<{ id: string; title: string } | null>(null)

  const { data: requests, isPending, isError, error } = useQuery({
    queryKey: financeQueryKeys.procurementRequests(statusFilter),
    queryFn: () => listProcurementRequests({ status: statusFilter || undefined, limit: FINANCE_LIST_LIMIT }),
  })

  const {
    data: summary,
    isError: summaryIsError,
    error: summaryError,
  } = useQuery({
    queryKey: financeQueryKeys.procurementSummary,
    queryFn: () => getProcurementSummary(),
  })

  const cancelMutation = useMutation({
    mutationFn: (id: string) => deleteProcurementRequest(id),
    onSuccess: () => {
      invalidate()
      setPendingCancel(null)
    },
    onError: (e: unknown) => notifyToast(userFacingMessageFromUnknown(e)),
  })

  function invalidate() {
    invalidateFinanceQueries(
      queryClient,
      financeQueryKeys.procurementRequestsRoot,
      financeQueryKeys.procurementSummary,
    )
  }

  return (
    <div>
      {summaryIsError && <p className="text-danger">{userFacingMessageFromUnknown(summaryError)}</p>}
      {summary && summary.total > 0 && (
        <div className={styles.summaryCard}>
          <span>
            Всего заявок: <b>{summary.total}</b>
          </span>
          {(Object.entries(summary.by_status) as [ProcurementStatus, number][])
            .filter(([, count]) => count > 0)
            .map(([status, count]) => (
              <span key={status}>
                {PROCUREMENT_STATUS_LABELS[status]}: <b>{count}</b>
              </span>
            ))}
          {Number(summary.total_budget) > 0 && (
            <span>
              Бюджет: <b>{Number(summary.total_budget).toLocaleString('ru-RU')} руб.</b>
            </span>
          )}
        </div>
      )}
      <div className="filter-bar">
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="filter-select"
          aria-label="Статус заявки"
        >
          <option value="">Все статусы</option>
          {(Object.entries(PROCUREMENT_STATUS_LABELS) as [ProcurementStatus, string][]).map(([val, label]) => (
            <option key={val} value={val}>
              {label}
            </option>
          ))}
        </select>
        {canCreate && (
          <button type="button" className="btn-primary" onClick={() => setShowForm((v) => !v)}>
            {showForm ? 'Отмена' : '+ Заявка'}
          </button>
        )}
      </div>

      {showForm && canCreate && (
        <ProcurementForm
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
      ) : !requests || requests.length === 0 ? (
        <p className="text-muted">Закупочных заявок нет</p>
      ) : (
        <div className={styles.tableWrapper}>
          <table className={styles.table}>
            <thead>
              <tr className={styles.theadRow}>
                <th className={styles.th}>Название</th>
                <th className={styles.th}>Контрагент</th>
                <th className={styles.th}>Сумма</th>
                <th className={styles.th}>Статус</th>
                <th className={styles.th}>Создана</th>
                <th className={styles.th}></th>
              </tr>
            </thead>
            <tbody>
              {requests.map((r) => (
                <ProcurementRequestRow
                  key={r.id}
                  request={r}
                  onUpdated={invalidate}
                  isCancelling={cancelMutation.isPending && cancelMutation.variables === r.id}
                  onCancel={() => setPendingCancel({ id: r.id, title: r.title })}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}

      {pendingCancel ? (
        <ConfirmDialog
          open
          title="Отменить заявку?"
          message={`Заявка «${pendingCancel.title}» будет переведена в статус «Отменена».`}
          confirmLabel="Отменить"
          cancelLabel="Закрыть"
          destructive
          disabled={cancelMutation.isPending}
          onConfirm={() => cancelMutation.mutate(pendingCancel.id)}
          onCancel={() => {
            if (!cancelMutation.isPending) setPendingCancel(null)
          }}
        />
      ) : null}
    </div>
  )
}
