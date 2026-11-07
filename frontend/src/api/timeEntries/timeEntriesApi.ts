import type {
  PagedResponse,
  PortalSpecialistMonthlySummary,
  PortalTimeEntry,
  TimeEntryBulkCreate,
  TimeEntryCreate,
  TimeEntryImportResult,
  TimeEntryPatch,
  TimeEntrySummary,
  TimeEntryReportBucket,
} from '../../types/timeEntry'
import { parseJsonOrThrowApi } from '../parseResponse'
import { authenticatedFetch } from '../rawClient'
import { filenameFromContentDisposition, triggerBlobDownload } from '../../utils/downloadBlob'
import { userFacingMessageFromApiFailure } from '../../utils/apiUserMessage'

export async function listTimeEntries(params?: {
  user_sub?: string
  date_from?: string
  date_to?: string
  month?: string
  task_id?: string
  limit?: number
  offset?: number
}): Promise<PagedResponse<PortalTimeEntry>> {
  const qs = new URLSearchParams()
  if (params?.user_sub) qs.set('user_sub', params.user_sub)
  if (params?.date_from) qs.set('date_from', params.date_from)
  if (params?.date_to) qs.set('date_to', params.date_to)
  if (params?.month) qs.set('month', params.month)
  if (params?.task_id) qs.set('task_id', params.task_id)
  if (params?.limit !== undefined) qs.set('limit', String(params.limit))
  if (params?.offset !== undefined) qs.set('offset', String(params.offset))
  const query = qs.toString() ? `?${qs}` : ''
  const res = await authenticatedFetch(`/portal/time-entries${query}`)
  return parseJsonOrThrowApi(res)
}

export async function getTimeEntrySummary(params?: {
  user_sub?: string
  date_from?: string
  date_to?: string
  task_id?: string
}): Promise<TimeEntrySummary> {
  const qs = new URLSearchParams()
  if (params?.user_sub) qs.set('user_sub', params.user_sub)
  if (params?.date_from) qs.set('date_from', params.date_from)
  if (params?.date_to) qs.set('date_to', params.date_to)
  if (params?.task_id) qs.set('task_id', params.task_id)
  const query = qs.toString() ? `?${qs}` : ''
  const res = await authenticatedFetch(`/portal/time-entries/summary${query}`)
  return parseJsonOrThrowApi(res)
}

export async function getTimeEntriesReport(params?: {
  group_by?: 'week' | 'month'
  user_sub?: string
  date_from?: string
  date_to?: string
  task_id?: string
}): Promise<TimeEntryReportBucket[]> {
  const qs = new URLSearchParams()
  if (params?.group_by) qs.set('group_by', params.group_by)
  if (params?.user_sub) qs.set('user_sub', params.user_sub)
  if (params?.date_from) qs.set('date_from', params.date_from)
  if (params?.date_to) qs.set('date_to', params.date_to)
  if (params?.task_id) qs.set('task_id', params.task_id)
  const query = qs.toString() ? `?${qs}` : ''
  const res = await authenticatedFetch(`/portal/time-entries/report${query}`)
  return parseJsonOrThrowApi(res)
}

export async function createTimeEntry(body: TimeEntryCreate): Promise<PortalTimeEntry> {
  const res = await authenticatedFetch('/portal/time-entries', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return parseJsonOrThrowApi(res)
}

export async function createTimeEntriesBulk(body: TimeEntryBulkCreate): Promise<PortalTimeEntry[]> {
  const res = await authenticatedFetch('/portal/time-entries/bulk', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return parseJsonOrThrowApi(res)
}

export async function importJiraTimeEntriesCsv(file: File): Promise<TimeEntryImportResult> {
  const form = new FormData()
  form.append('file', file)
  const res = await authenticatedFetch('/portal/time-entries/import-jira-csv', {
    method: 'POST',
    body: form,
  })
  return parseJsonOrThrowApi(res)
}

export async function patchTimeEntry(entryId: string, body: TimeEntryPatch): Promise<PortalTimeEntry> {
  const res = await authenticatedFetch(`/portal/time-entries/${entryId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return parseJsonOrThrowApi(res)
}

export async function deleteTimeEntry(entryId: string): Promise<void> {
  const res = await authenticatedFetch(`/portal/time-entries/${entryId}`, { method: 'DELETE' })
  await parseJsonOrThrowApi<void>(res)
}

export async function listSpecialistsSummary(params: {
  month: string
  limit?: number
  offset?: number
}): Promise<PagedResponse<PortalSpecialistMonthlySummary>> {
  const qs = new URLSearchParams()
  qs.set('month', params.month)
  if (params.limit !== undefined) qs.set('limit', String(params.limit))
  if (params.offset !== undefined) qs.set('offset', String(params.offset))
  const res = await authenticatedFetch(`/portal/time-entries/specialists?${qs}`)
  return parseJsonOrThrowApi(res)
}

export async function exportTimeEntries(params: {
  format: 'csv' | 'xlsx' | 'pdf'
  month: string
  user_sub?: string
}): Promise<void> {
  const qs = new URLSearchParams()
  qs.set('format', params.format)
  qs.set('month', params.month)
  if (params.user_sub) qs.set('user_sub', params.user_sub)
  const res = await authenticatedFetch(`/portal/time-entries/export?${qs}`)
  if (!res.ok) {
    const bodyText = await res.text().catch(() => '')
    throw new Error(userFacingMessageFromApiFailure(res.status, bodyText))
  }
  const blob = await res.blob()
  const filename = filenameFromContentDisposition(
    res.headers.get('Content-Disposition'),
    `timesheets_${params.month}.${params.format}`,
  )
  triggerBlobDownload(blob, filename)
}
