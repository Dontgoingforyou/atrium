import type {
  ContractCreate,
  ContractPatch,
  CounterpartyCreate,
  CounterpartyPatch,
  FinanceSummary,
  InvoiceCreate,
  InvoicePatch,
  PaymentCreate,
  PortalContract,
  PortalCounterparty,
  PortalInvoice,
  PortalPayment,
  PortalProcurementRequest,
  ProcurementRequestCreate,
  ProcurementRequestPatch,
  ProcurementSummary,
} from '../../types/finance'
import { parseJsonOrThrowApi } from '../parseResponse'
import { authenticatedFetch } from '../rawClient'

const BASE = '/portal/finance'

// --- Контрагенты ---

export async function listCounterparties(params?: {
  limit?: number
  offset?: number
}): Promise<PortalCounterparty[]> {
  const qs = new URLSearchParams()
  if (params?.limit !== undefined) qs.set('limit', String(params.limit))
  if (params?.offset !== undefined) qs.set('offset', String(params.offset))
  const query = qs.toString() ? `?${qs}` : ''
  const res = await authenticatedFetch(`${BASE}/counterparties${query}`)
  return parseJsonOrThrowApi(res)
}

export async function createCounterparty(body: CounterpartyCreate): Promise<PortalCounterparty> {
  const res = await authenticatedFetch(`${BASE}/counterparties`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return parseJsonOrThrowApi(res)
}

export async function patchCounterparty(id: string, body: CounterpartyPatch): Promise<PortalCounterparty> {
  const res = await authenticatedFetch(`${BASE}/counterparties/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return parseJsonOrThrowApi(res)
}

// --- Договоры ---

export async function listContracts(params?: {
  status?: string
  contract_type?: string
  counterparty_id?: string
  limit?: number
  offset?: number
}): Promise<PortalContract[]> {
  const qs = new URLSearchParams()
  if (params?.status) qs.set('status', params.status)
  if (params?.contract_type) qs.set('contract_type', params.contract_type)
  if (params?.counterparty_id) qs.set('counterparty_id', params.counterparty_id)
  if (params?.limit !== undefined) qs.set('limit', String(params.limit))
  if (params?.offset !== undefined) qs.set('offset', String(params.offset))
  const query = qs.toString() ? `?${qs}` : ''
  const res = await authenticatedFetch(`${BASE}/contracts${query}`)
  return parseJsonOrThrowApi(res)
}

export async function createContract(body: ContractCreate): Promise<PortalContract> {
  const res = await authenticatedFetch(`${BASE}/contracts`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return parseJsonOrThrowApi(res)
}

export async function getContract(id: string): Promise<PortalContract> {
  const res = await authenticatedFetch(`${BASE}/contracts/${id}`)
  return parseJsonOrThrowApi(res)
}

export async function patchContract(id: string, body: ContractPatch): Promise<PortalContract> {
  const res = await authenticatedFetch(`${BASE}/contracts/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return parseJsonOrThrowApi(res)
}

export async function deleteContract(id: string): Promise<void> {
  const res = await authenticatedFetch(`${BASE}/contracts/${id}`, { method: 'DELETE' })
  await parseJsonOrThrowApi<void>(res)
}

// --- Счета и акты ---

export async function listInvoices(params?: {
  status?: string
  invoice_type?: string
  contract_id?: string
  limit?: number
  offset?: number
}): Promise<PortalInvoice[]> {
  const qs = new URLSearchParams()
  if (params?.status) qs.set('status', params.status)
  if (params?.invoice_type) qs.set('invoice_type', params.invoice_type)
  if (params?.contract_id) qs.set('contract_id', params.contract_id)
  if (params?.limit !== undefined) qs.set('limit', String(params.limit))
  if (params?.offset !== undefined) qs.set('offset', String(params.offset))
  const query = qs.toString() ? `?${qs}` : ''
  const res = await authenticatedFetch(`${BASE}/invoices${query}`)
  return parseJsonOrThrowApi(res)
}

export async function createInvoice(body: InvoiceCreate): Promise<PortalInvoice> {
  const res = await authenticatedFetch(`${BASE}/invoices`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return parseJsonOrThrowApi(res)
}

export async function patchInvoice(id: string, body: InvoicePatch): Promise<PortalInvoice> {
  const res = await authenticatedFetch(`${BASE}/invoices/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return parseJsonOrThrowApi(res)
}

// --- Платежи ---

export async function listPayments(params?: {
  invoice_id?: string
  limit?: number
  offset?: number
}): Promise<PortalPayment[]> {
  const qs = new URLSearchParams()
  if (params?.invoice_id) qs.set('invoice_id', params.invoice_id)
  if (params?.limit !== undefined) qs.set('limit', String(params.limit))
  if (params?.offset !== undefined) qs.set('offset', String(params.offset))
  const query = qs.toString() ? `?${qs}` : ''
  const res = await authenticatedFetch(`${BASE}/payments${query}`)
  return parseJsonOrThrowApi(res)
}

export async function createPayment(body: PaymentCreate): Promise<PortalPayment> {
  const res = await authenticatedFetch(`${BASE}/payments`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return parseJsonOrThrowApi(res)
}

export async function deletePayment(id: string): Promise<void> {
  const res = await authenticatedFetch(`${BASE}/payments/${id}`, { method: 'DELETE' })
  await parseJsonOrThrowApi<void>(res)
}

// --- Отчёты ---

export async function getFinanceSummary(): Promise<FinanceSummary> {
  const res = await authenticatedFetch(`${BASE}/summary`)
  return parseJsonOrThrowApi(res)
}

// --- Закупочные заявки (эпик 17) ---

export async function listProcurementRequests(params?: {
  status?: string
  counterparty_id?: string
  limit?: number
  offset?: number
}): Promise<PortalProcurementRequest[]> {
  const qs = new URLSearchParams()
  if (params?.status) qs.set('status', params.status)
  if (params?.counterparty_id) qs.set('counterparty_id', params.counterparty_id)
  if (params?.limit !== undefined) qs.set('limit', String(params.limit))
  if (params?.offset !== undefined) qs.set('offset', String(params.offset))
  const query = qs.toString() ? `?${qs}` : ''
  const res = await authenticatedFetch(`${BASE}/procurement-requests${query}`)
  return parseJsonOrThrowApi(res)
}

export async function createProcurementRequest(
  body: ProcurementRequestCreate,
): Promise<PortalProcurementRequest> {
  const res = await authenticatedFetch(`${BASE}/procurement-requests`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return parseJsonOrThrowApi(res)
}

export async function getProcurementRequest(id: string): Promise<PortalProcurementRequest> {
  const res = await authenticatedFetch(`${BASE}/procurement-requests/${id}`)
  return parseJsonOrThrowApi(res)
}

export async function patchProcurementRequest(
  id: string,
  body: ProcurementRequestPatch,
): Promise<PortalProcurementRequest> {
  const res = await authenticatedFetch(`${BASE}/procurement-requests/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return parseJsonOrThrowApi(res)
}

export async function deleteProcurementRequest(id: string): Promise<void> {
  const res = await authenticatedFetch(`${BASE}/procurement-requests/${id}`, { method: 'DELETE' })
  await parseJsonOrThrowApi<void>(res)
}

export async function getProcurementSummary(): Promise<ProcurementSummary> {
  const res = await authenticatedFetch(`${BASE}/procurement-summary`)
  return parseJsonOrThrowApi(res)
}

// --- Пользователи портала (для поиска) ---

export type { PortalUserShort } from '../usersApi'
export { listPortalUsers } from '../usersApi'
