import type {
  ContractStatus,
  ContractType,
  CounterpartyType,
  InvoiceStatus,
  InvoiceType,
  PaymentCategory,
  ProcurementStatus,
} from '../../types/finance'

export const CONTRACT_TYPE_LABELS: Record<ContractType, string> = {
  active: 'Действующий',
  template: 'Шаблон',
}

export const INVOICE_TYPE_LABELS: Record<InvoiceType, string> = {
  invoice: 'Счёт',
  act: 'Акт',
}

export const CONTRACT_STATUS_LABELS: Record<ContractStatus, string> = {
  draft: 'Черновик',
  active: 'Активный',
  completed: 'Завершён',
  cancelled: 'Отменён',
}

export const INVOICE_STATUS_LABELS: Record<InvoiceStatus, string> = {
  draft: 'Черновик',
  sent: 'Отправлен',
  paid: 'Оплачен',
  overdue: 'Просрочен',
  cancelled: 'Отменён',
}

export const COUNTERPARTY_TYPE_LABELS: Record<CounterpartyType, string> = {
  vendor: 'Поставщик',
  client: 'Клиент',
  partner: 'Партнёр',
}

export const PAYMENT_CATEGORY_LABELS: Record<PaymentCategory, string> = {
  contract: 'По договору',
  admin_expense: 'Адм. расходы',
  other: 'Прочее',
}

export const PROCUREMENT_STATUS_LABELS: Record<ProcurementStatus, string> = {
  draft: 'Черновик',
  pending_approval: 'На согласовании',
  approved: 'Утверждена',
  rejected: 'Отклонена',
  in_progress: 'В работе',
  completed: 'Завершена',
  cancelled: 'Отменена',
}

export const PROCUREMENT_STATUS_COLORS: Partial<Record<ProcurementStatus, string>> = {
  approved: 'var(--color-success)',
  rejected: 'var(--color-danger)',
  cancelled: 'var(--color-text-muted)',
  completed: 'var(--color-success)',
  in_progress: 'var(--color-primary)',
}
