import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { deletePayment, listPayments } from '../../api/finance/financeApi'
import { PAYMENT_CATEGORY_LABELS } from '../../domain/finance/financeUi'
import { userFacingMessageFromUnknown } from '../../utils/apiUserMessage'
import { useNotifyToast } from '../../hooks/useNotifyToast'
import { ConfirmDialog } from '../../components/ui/ConfirmDialog'
import { useAuthStore } from '../../store/authStore'
import styles from '@/styles/modules/finance/FinancePage.module.css'
import { canMutateOwnedFinanceRecord } from './financeAccess'
import { PaymentForm } from './PaymentForm'
import { FINANCE_LIST_LIMIT, financeQueryKeys, invalidateFinanceQueries } from './financeQueryKeys'

export function PaymentsTab() {
  const queryClient = useQueryClient()
  const notifyToast = useNotifyToast()
  const user = useAuthStore((s) => s.user)
  const [showForm, setShowForm] = useState(false)
  const [pendingDelete, setPendingDelete] = useState<{ id: string; amount: string; currency: string } | null>(
    null,
  )

  const { data: payments, isPending, isError, error } = useQuery({
    queryKey: financeQueryKeys.payments,
    queryFn: () => listPayments({ limit: FINANCE_LIST_LIMIT }),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deletePayment(id),
    onSuccess: () => {
      invalidate()
      setPendingDelete(null)
    },
    onError: (e: unknown) => notifyToast(userFacingMessageFromUnknown(e), { silent: true }),
  })

  function invalidate() {
    invalidateFinanceQueries(queryClient, financeQueryKeys.payments, financeQueryKeys.summary)
  }

  return (
    <div>
      <div className="filter-bar">
        <button type="button" className="btn-primary" onClick={() => setShowForm((v) => !v)}>
          {showForm ? 'Отмена' : '+ Платёж'}
        </button>
      </div>

      {showForm && (
        <PaymentForm
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
      ) : !payments || payments.length === 0 ? (
        <p className="text-muted">Платежей нет</p>
      ) : (
        <div className={styles.tableWrapper}>
          <table className={styles.table}>
            <thead>
              <tr className={styles.theadRow}>
                <th className={styles.th}>Сумма</th>
                <th className={styles.th}>Валюта</th>
                <th className={styles.th}>Счёт</th>
                <th className={styles.th}>Категория</th>
                <th className={styles.th}>Дата</th>
                <th className={styles.th}>Примечание</th>
                <th className={styles.th}>Автор</th>
                <th className={styles.th}></th>
              </tr>
            </thead>
            <tbody>
              {payments.map((p) => {
                const canDelete = canMutateOwnedFinanceRecord(p.author_sub, user)
                return (
                  <tr key={p.id} className={styles.tbodyRow}>
                    <td className={`${styles.td} ${styles.tdBold}`}>
                      {Number(p.amount).toLocaleString('ru-RU')}
                    </td>
                    <td className={styles.td}>{p.currency}</td>
                    <td className={`${styles.td} ${styles.tdMuted}`}>{p.invoice?.title ?? '—'}</td>
                    <td className={styles.td}>
                      {PAYMENT_CATEGORY_LABELS[p.payment_category] ?? p.payment_category}
                    </td>
                    <td className={styles.td}>{p.paid_at ?? '—'}</td>
                    <td className={`${styles.td} ${styles.tdMuted}`}>{p.note ?? '—'}</td>
                    <td className={`${styles.td} ${styles.tdMuted} ${styles.authorCell}`}>{p.author_sub}</td>
                    <td className={styles.tdActions}>
                      {canDelete && (
                        <button
                          type="button"
                          onClick={() =>
                            setPendingDelete({ id: p.id, amount: p.amount, currency: p.currency })
                          }
                          disabled={deleteMutation.isPending && deleteMutation.variables === p.id}
                          className={styles.btnDanger}
                        >
                          Удалить
                        </button>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {pendingDelete ? (
        <ConfirmDialog
          open
          title="Удалить платёж?"
          message={`Платёж на ${Number(pendingDelete.amount).toLocaleString('ru-RU')} ${pendingDelete.currency} будет удалён без возможности восстановления.`}
          confirmLabel="Удалить"
          cancelLabel="Отмена"
          destructive
          confirmSound="error"
          disabled={deleteMutation.isPending}
          onConfirm={() => deleteMutation.mutate(pendingDelete.id)}
          onCancel={() => {
            if (!deleteMutation.isPending) setPendingDelete(null)
          }}
        />
      ) : null}
    </div>
  )
}
