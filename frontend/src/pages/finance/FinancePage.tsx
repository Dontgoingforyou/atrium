import { useState } from 'react'
import { ContractsTab } from './ContractsTab'
import { InvoicesTab } from './InvoicesTab'
import { PaymentsTab } from './PaymentsTab'
import { CounterpartiesTab } from './CounterpartiesTab'
import { ProcurementTab } from './ProcurementTab'
import { SummaryBar } from './SummaryBar'
import tabStyles from '@/styles/modules/common/Tabs.module.css'

const TABS = ['contracts', 'invoices', 'payments', 'counterparties', 'procurement'] as const
type Tab = (typeof TABS)[number]

const TAB_LABELS: Record<Tab, string> = {
  contracts: 'Договоры',
  invoices: 'Счета и акты',
  payments: 'Платежи',
  counterparties: 'Контрагенты',
  procurement: 'Закупочные заявки',
}

export function FinancePage() {
  const [tab, setTab] = useState<Tab>('contracts')
  const [invoiceStatusFilter, setInvoiceStatusFilter] = useState('')

  function openOverdueInvoices() {
    setInvoiceStatusFilter('overdue')
    setTab('invoices')
  }

  function handleTabKeyDown(e: React.KeyboardEvent<HTMLDivElement>) {
    const idx = TABS.indexOf(tab)
    if (idx < 0) return
    if (e.key === 'ArrowRight') {
      e.preventDefault()
      setTab(TABS[(idx + 1) % TABS.length])
    } else if (e.key === 'ArrowLeft') {
      e.preventDefault()
      setTab(TABS[(idx - 1 + TABS.length) % TABS.length])
    } else if (e.key === 'Home') {
      e.preventDefault()
      setTab(TABS[0])
    } else if (e.key === 'End') {
      e.preventDefault()
      setTab(TABS[TABS.length - 1])
    }
  }

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Финансы</h1>
      </div>

      <SummaryBar onOverdueClick={openOverdueInvoices} />

      <div
        className={tabStyles.tabs}
        role="tablist"
        aria-label="Разделы финансов"
        onKeyDown={handleTabKeyDown}
      >
        {TABS.map((t) => (
          <button
            key={t}
            type="button"
            role="tab"
            aria-selected={tab === t}
            tabIndex={tab === t ? 0 : -1}
            onClick={() => setTab(t)}
            className={`${tabStyles.tab} ${tab === t ? tabStyles.tabActive : ''}`}
          >
            {TAB_LABELS[t]}
          </button>
        ))}
      </div>

      {tab === 'contracts' && <ContractsTab />}
      {tab === 'invoices' && (
        <InvoicesTab
          statusFilter={invoiceStatusFilter}
          onStatusFilterChange={setInvoiceStatusFilter}
        />
      )}
      {tab === 'payments' && <PaymentsTab />}
      {tab === 'counterparties' && <CounterpartiesTab />}
      {tab === 'procurement' && <ProcurementTab />}
    </div>
  )
}
