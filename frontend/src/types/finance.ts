export type CounterpartyType = 'vendor' | 'client' | 'partner'
export type ContractType = 'template' | 'active'
export type ContractStatus = 'draft' | 'active' | 'completed' | 'cancelled'
export type InvoiceType = 'invoice' | 'act'
export type InvoiceStatus = 'draft' | 'sent' | 'paid' | 'overdue' | 'cancelled'
export type PaymentCategory = 'contract' | 'admin_expense' | 'other'

export interface PortalCounterparty {
  id: string
  name: string
  inn: string | null
  contact_email: string | null
  contact_phone: string | null
  counterparty_type: CounterpartyType
  note: string | null
  is_active: boolean
  author_sub: string
  created_at: string
  updated_at: string
}

export interface CounterpartyCreate {
  name: string
  inn?: string | null
  contact_email?: string | null
  contact_phone?: string | null
  counterparty_type?: CounterpartyType
  note?: string | null
  is_active?: boolean
}

export interface CounterpartyPatch {
  name?: string
  inn?: string | null
  contact_email?: string | null
  contact_phone?: string | null
  counterparty_type?: CounterpartyType
  note?: string | null
  is_active?: boolean
}

export interface CounterpartyShort {
  id: string
  name: string
}

export interface UserShort {
  sub: string
  full_name: string | null
  email: string | null
  username: string | null
}

export interface PortalContract {
  id: string
  title: string
  contract_type: ContractType
  counterparty_id: string | null
  counterparty: CounterpartyShort | null
  amount: string | null
  currency: string
  start_date: string | null
  end_date: string | null
  status: ContractStatus
  document_id: string | null
  author_sub: string
  author_profile: UserShort | null
  owner_sub: string | null
  owner_profile: UserShort | null
  created_at: string
  updated_at: string
}

export interface ContractCreate {
  title: string
  contract_type?: ContractType
  counterparty_id?: string | null
  amount?: string | null
  currency?: string
  start_date?: string | null
  end_date?: string | null
  status?: ContractStatus
  document_id?: string | null
  owner_sub?: string | null
}

export interface ContractPatch {
  title?: string
  contract_type?: ContractType
  counterparty_id?: string | null
  amount?: string | null
  currency?: string
  start_date?: string | null
  end_date?: string | null
  status?: ContractStatus
  document_id?: string | null
  owner_sub?: string | null
}

export interface PortalInvoice {
  id: string
  title: string
  contract_id: string | null
  contract: { id: string; title: string } | null
  invoice_type: InvoiceType
  amount: string | null
  currency: string
  issue_date: string | null
  due_date: string | null
  status: InvoiceStatus
  author_sub: string
  created_at: string
  updated_at: string
}

export interface InvoiceCreate {
  title: string
  contract_id?: string | null
  invoice_type?: InvoiceType
  amount?: string | null
  currency?: string
  issue_date?: string | null
  due_date?: string | null
  status?: InvoiceStatus
}

export interface InvoicePatch {
  title?: string
  contract_id?: string | null
  invoice_type?: InvoiceType
  amount?: string | null
  currency?: string
  issue_date?: string | null
  due_date?: string | null
  status?: InvoiceStatus
}

export interface PortalPayment {
  id: string
  invoice_id: string | null
  invoice: { id: string; title: string } | null
  amount: string
  currency: string
  paid_at: string | null
  note: string | null
  payment_category: PaymentCategory
  author_sub: string
  created_at: string
}

export interface PaymentCreate {
  invoice_id?: string | null
  amount: string
  currency?: string
  paid_at?: string | null
  note?: string | null
  payment_category?: PaymentCategory
}

export interface FinanceSummary {
  contracts_total: number
  contracts_active: number
  invoices_total: number
  invoices_paid: number
  invoices_overdue: number
  payments_total_amount: string
  payments_count: number
}

// --- Закупки (эпик 17) ---

export type ProcurementStatus =
  | 'draft'
  | 'pending_approval'
  | 'approved'
  | 'rejected'
  | 'in_progress'
  | 'completed'
  | 'cancelled'

export interface PortalProcurementRequest {
  id: string
  title: string
  description: string | null
  status: ProcurementStatus
  counterparty_id: string | null
  counterparty: CounterpartyShort | null
  amount: string | null
  currency: string
  document_id: string | null
  author_sub: string
  created_at: string
  updated_at: string
}

export interface ProcurementRequestCreate {
  title: string
  description?: string | null
  counterparty_id?: string | null
  amount?: string | null
  currency?: string
  document_id?: string | null
  status?: ProcurementStatus
}

export interface ProcurementRequestPatch {
  title?: string
  description?: string | null
  counterparty_id?: string | null
  amount?: string | null
  currency?: string
  document_id?: string | null
  status?: ProcurementStatus
}

export interface ProcurementSummary {
  total: number
  by_status: Record<ProcurementStatus, number>
  total_budget: string
}
