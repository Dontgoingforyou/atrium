import { useQuery } from '@tanstack/react-query'
import { getFinanceSummary, listInvoices } from '../../api/finance/financeApi'
import { userFacingMessageFromUnknown } from '../../utils/apiUserMessage'
import styles from '@/styles/modules/finance/FinancePage.module.css'
import { FINANCE_LIST_LIMIT, financeQueryKeys } from './financeQueryKeys'

export function SummaryBar({ onOverdueClick }: { onOverdueClick: () => void }) {
  const { data, isError, error } = useQuery({
    queryKey: financeQueryKeys.summary,
    queryFn: () => getFinanceSummary(),
  })

  const overdueCount = data?.invoices_overdue ?? 0
  const {
    data: overdueInvoices,
    isError: overdueIsError,
    error: overdueError,
  } = useQuery({
    queryKey: financeQueryKeys.invoices({ status: 'overdue', invoiceType: '' }),
    queryFn: () => listInvoices({ status: 'overdue', limit: FINANCE_LIST_LIMIT }),
    enabled: overdueCount > 0,
  })

  if (isError) {
    return <p className="text-danger">{userFacingMessageFromUnknown(error)}</p>
  }

  if (!data) return null

  const hasOverdue = overdueInvoices && overdueInvoices.length > 0
  const hiddenOverdue =
    overdueInvoices && overdueCount > overdueInvoices.length ? overdueCount - overdueInvoices.length : 0

  return (
    <>
      <div
        className={`${styles.summaryBar} ${hasOverdue ? styles.summaryBarWithOverdue : styles.summaryBarNoOverdue}`}
      >
        <span>
          Договоры: <b>{data.contracts_active}</b> активных / {data.contracts_total} всего
        </span>
        <span>
          Счета: <b className={styles.summaryPaid}>{data.invoices_paid}</b> оплачено
          {data.invoices_overdue > 0 && (
            <button type="button" className={styles.overdueBtn} onClick={onOverdueClick}>
              · {data.invoices_overdue} просрочено ↓
            </button>
          )}
        </span>
        <span>
          Платежей: <b>{data.payments_count}</b> на сумму{' '}
          <b>{Number(data.payments_total_amount).toLocaleString('ru-RU')} руб.</b>
        </span>
      </div>

      {overdueIsError && (
        <p className="text-danger">{userFacingMessageFromUnknown(overdueError)}</p>
      )}

      {hasOverdue && (
        <div className={styles.overdueAlert}>
          <div className={styles.overdueAlertTitle}>Требует внимания — просроченные счета</div>
          <div className={styles.overdueList}>
            {overdueInvoices.map((inv) => (
              <div key={inv.id} className={styles.overdueItem}>
                <span className={styles.overdueItemTitle}>{inv.title}</span>
                {inv.amount && (
                  <span className={styles.overdueItemAmount}>
                    {Number(inv.amount).toLocaleString('ru-RU')} {inv.currency}
                  </span>
                )}
                {inv.due_date && (
                  <span className={styles.overdueItemDate}>
                    срок: {new Date(inv.due_date).toLocaleDateString('ru-RU')}
                  </span>
                )}
              </div>
            ))}
          </div>
          {hiddenOverdue > 0 && (
            <div className={styles.overdueMore}>и ещё {hiddenOverdue}</div>
          )}
        </div>
      )}
    </>
  )
}
