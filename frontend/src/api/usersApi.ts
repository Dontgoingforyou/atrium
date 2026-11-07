import { parseJsonOrThrowApi } from './parseResponse'
import { authenticatedFetch } from './rawClient'
import type { PagedResponse } from '../types/timeEntry'
import type { PortalUser, UserPresence } from '../types/user'

export type { PortalUser, UserPresence } from '../types/user'
/** @deprecated Алиас PortalUser — оставляем имя для существующих импортов. */
export type PortalUserShort = PortalUser

export type PortalUserPresenceRow = {
  sub: string
  presence: UserPresence
  /** ISO-метка последней активности из Redis */
  last_seen_at?: string | null
}

/**
 * Список пользователей портала (публичные профили).
 *
 * Backend отдаёт `PagedResponse` — здесь разворачиваем в голый массив,
 * так как ни один текущий потребитель (канбан, пикеры, справочник) не строит постраничную
 * навигацию по этому списку, а лишь запрашивает его целиком (limit по умолчанию 500).
 */
export async function listPortalUsers(params?: { limit?: number }): Promise<PortalUser[]> {
  const qs = new URLSearchParams()
  if (params?.limit !== undefined) qs.set('limit', String(params.limit))
  const query = qs.toString() ? `?${qs}` : ''
  const res = await authenticatedFetch(`/portal/users${query}`)
  const page = await parseJsonOrThrowApi<PagedResponse<PortalUser>>(res)
  return page.items
}

/** Студенты портала (профиль с ``portal_chat_allowed=false``): только менеджер/админ. */
export async function listPortalStudentSpecialists(params?: {
  limit?: number
  skip?: number
}): Promise<PagedResponse<PortalUser>> {
  const qs = new URLSearchParams()
  if (params?.limit !== undefined) qs.set('limit', String(params.limit))
  if (params?.skip !== undefined) qs.set('skip', String(params.skip))
  const query = qs.toString() ? `?${qs}` : ''
  const res = await authenticatedFetch(`/portal/users/specialists${query}`)
  return parseJsonOrThrowApi(res)
}

/**
 * Тот же набор и порядок, что у ``listPortalUsers``, только ``sub`` + ``presence`` (без presigned аватаров).
 */
export async function listPortalUsersPresence(params?: {
  limit?: number
  skip?: number
}): Promise<PortalUserPresenceRow[]> {
  const qs = new URLSearchParams()
  if (params?.limit !== undefined) qs.set('limit', String(params.limit))
  if (params?.skip !== undefined) qs.set('skip', String(params.skip))
  const query = qs.toString() ? `?${qs}` : ''
  const res = await authenticatedFetch(`/portal/users/presence${query}`)
  const page = await parseJsonOrThrowApi<PagedResponse<PortalUserPresenceRow>>(res)
  return page.items
}

export async function postPortalPresence(body: { visible: boolean; active: boolean }): Promise<void> {
  const res = await authenticatedFetch('/portal/users/me/presence', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  await parseJsonOrThrowApi(res)
}

export async function uploadMyAvatar(
  file: File,
): Promise<{ avatar_url: string; avatar_focal_x?: number | null; avatar_focal_y?: number | null }> {
  const body = new FormData()
  body.append('file', file)
  const res = await authenticatedFetch('/portal/users/me/avatar', {
    method: 'POST',
    body,
  })
  return parseJsonOrThrowApi(res)
}

export async function deleteMyAvatar(): Promise<void> {
  const res = await authenticatedFetch('/portal/users/me/avatar', { method: 'DELETE' })
  await parseJsonOrThrowApi<void>(res)
}
