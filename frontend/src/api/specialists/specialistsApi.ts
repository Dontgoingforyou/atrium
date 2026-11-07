import { createCommentThreadApi } from '../commentThreadApi'
import { parseJsonOrThrowApi } from '../parseResponse'
import { authenticatedFetch } from '../rawClient'
import type { ThreadCommentCreate, ThreadCommentUpdate } from '../../types/commentThread'
import type { RichMediaRead } from '../../types/richMedia'
import type {
  ManagerSpecialistAdd,
  ManagerSpecialistEntry,
  ManagerSpecialistPatch,
  ManagerSpecialistReorder,
  SpecialistBoardPref,
  SpecialistBoardPrefWrite,
  SpecialistColumn,
  JiraSearchHit,
  SpecialistJiraState,
  SpecialistLink,
  SpecialistManagerRef,
  SpecialistNote,
  SpecialistProfile,
  SpecialistProfilePatch,
  SpecialistStatus,
} from '../../types/specialist'

// ---------------------------------------------------------------------------
// Колонки воронки
// ---------------------------------------------------------------------------

export async function listSpecialistColumns(): Promise<SpecialistColumn[]> {
  const res = await authenticatedFetch('/portal/specialists/columns')
  return parseJsonOrThrowApi(res)
}

export async function createSpecialistColumn(body: {
  key: string
  title: string
  color?: string
  position?: number
}): Promise<SpecialistColumn> {
  const res = await authenticatedFetch('/portal/specialists/columns', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return parseJsonOrThrowApi(res)
}

export async function updateSpecialistColumn(
  colId: string,
  body: { title?: string; color?: string; position?: number },
): Promise<SpecialistColumn> {
  const res = await authenticatedFetch(`/portal/specialists/columns/${colId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return parseJsonOrThrowApi(res)
}

export async function deleteSpecialistColumn(colId: string): Promise<void> {
  const res = await authenticatedFetch(`/portal/specialists/columns/${colId}`, {
    method: 'DELETE',
  })
  await parseJsonOrThrowApi<void>(res)
}

// ---------------------------------------------------------------------------
// Статусы специалистов
// ---------------------------------------------------------------------------

export async function listSpecialistStatuses(): Promise<SpecialistStatus[]> {
  const res = await authenticatedFetch('/portal/specialists/statuses')
  return parseJsonOrThrowApi(res)
}

export async function createSpecialistStatus(body: {
  title: string
  color?: string
}): Promise<SpecialistStatus> {
  const res = await authenticatedFetch('/portal/specialists/statuses', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return parseJsonOrThrowApi(res)
}

// ---------------------------------------------------------------------------
// Доска специалистов
// ---------------------------------------------------------------------------

export async function listBoardEntries(params?: {
  manager_sub?: string
  /** Справочник «Все специалисты»: все закрепления (менеджер и админ). */
  directory?: boolean
}): Promise<ManagerSpecialistEntry[]> {
  const qs = new URLSearchParams()
  if (params?.manager_sub) qs.set('manager_sub', params.manager_sub)
  if (params?.directory) qs.set('directory', 'true')
  const query = qs.toString() ? `?${qs}` : ''
  const res = await authenticatedFetch(`/portal/specialists/board${query}`)
  return parseJsonOrThrowApi(res)
}

export async function addToBoardApi(
  body: ManagerSpecialistAdd,
  params?: { manager_sub?: string },
): Promise<ManagerSpecialistEntry> {
  const qs = new URLSearchParams()
  if (params?.manager_sub) qs.set('manager_sub', params.manager_sub)
  const query = qs.toString() ? `?${qs}` : ''
  const res = await authenticatedFetch(`/portal/specialists/board${query}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return parseJsonOrThrowApi(res)
}

export async function moveOnBoardApi(
  specialistSub: string,
  body: ManagerSpecialistPatch,
  params?: { manager_sub?: string },
): Promise<ManagerSpecialistEntry> {
  const qs = new URLSearchParams()
  if (params?.manager_sub) qs.set('manager_sub', params.manager_sub)
  const query = qs.toString() ? `?${qs}` : ''
  const res = await authenticatedFetch(`/portal/specialists/board/${encodeURIComponent(specialistSub)}${query}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return parseJsonOrThrowApi(res)
}

export async function reorderOnBoardApi(
  body: ManagerSpecialistReorder,
  params?: { manager_sub?: string },
): Promise<ManagerSpecialistEntry> {
  const qs = new URLSearchParams()
  if (params?.manager_sub) qs.set('manager_sub', params.manager_sub)
  const query = qs.toString() ? `?${qs}` : ''
  const res = await authenticatedFetch(`/portal/specialists/board/reorder${query}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return parseJsonOrThrowApi(res)
}

export async function removeFromBoardApi(
  specialistSub: string,
  params?: { manager_sub?: string },
): Promise<void> {
  const qs = new URLSearchParams()
  if (params?.manager_sub) qs.set('manager_sub', params.manager_sub)
  const query = qs.toString() ? `?${qs}` : ''
  const res = await authenticatedFetch(
    `/portal/specialists/board/${encodeURIComponent(specialistSub)}${query}`,
    { method: 'DELETE' },
  )
  await parseJsonOrThrowApi<void>(res)
}

export async function reassignBoardManager(
  specialistSub: string,
  body: { from_manager_sub: string; to_manager_sub: string },
): Promise<void> {
  const res = await authenticatedFetch(
    `/portal/specialists/board/${encodeURIComponent(specialistSub)}/reassign-manager`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    },
  )
  await parseJsonOrThrowApi<void>(res)
}

export async function deleteSpecialistFromPortal(specialistSub: string): Promise<void> {
  const res = await authenticatedFetch(`/portal/specialists/${encodeURIComponent(specialistSub)}`, {
    method: 'DELETE',
  })
  await parseJsonOrThrowApi<void>(res)
}

export async function listManagersForSpecialist(specialistSub: string): Promise<SpecialistManagerRef[]> {
  const res = await authenticatedFetch(
    `/portal/specialists/board/by-specialist?specialist_sub=${encodeURIComponent(specialistSub)}`,
  )
  return parseJsonOrThrowApi(res)
}

// ---------------------------------------------------------------------------
// Карточка специалиста — профиль
// ---------------------------------------------------------------------------

export async function getSpecialistProfile(specialistSub: string): Promise<SpecialistProfile> {
  const res = await authenticatedFetch(`/portal/specialists/${encodeURIComponent(specialistSub)}/profile`)
  return parseJsonOrThrowApi(res)
}

export async function patchSpecialistProfile(
  specialistSub: string,
  data: SpecialistProfilePatch,
): Promise<SpecialistProfile> {
  const res = await authenticatedFetch(`/portal/specialists/${encodeURIComponent(specialistSub)}/profile`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  return parseJsonOrThrowApi(res)
}

// ---------------------------------------------------------------------------
// Карточка специалиста — ссылки
// ---------------------------------------------------------------------------

export async function listSpecialistLinks(specialistSub: string): Promise<SpecialistLink[]> {
  const res = await authenticatedFetch(`/portal/specialists/${encodeURIComponent(specialistSub)}/links`)
  return parseJsonOrThrowApi(res)
}

export async function createSpecialistLink(
  specialistSub: string,
  data: { title: string; url: string },
): Promise<SpecialistLink> {
  const res = await authenticatedFetch(`/portal/specialists/${encodeURIComponent(specialistSub)}/links`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  return parseJsonOrThrowApi(res)
}

export async function deleteSpecialistLink(specialistSub: string, linkId: string): Promise<void> {
  const res = await authenticatedFetch(
    `/portal/specialists/${encodeURIComponent(specialistSub)}/links/${linkId}`,
    { method: 'DELETE' },
  )
  await parseJsonOrThrowApi<void>(res)
}

// ---------------------------------------------------------------------------
// Карточка специалиста — заметки
// ---------------------------------------------------------------------------

function specialistNotesApi(specialistSub: string) {
  return createCommentThreadApi(`/portal/specialists/${encodeURIComponent(specialistSub)}/notes`)
}

export async function listSpecialistNotes(specialistSub: string): Promise<SpecialistNote[]> {
  return specialistNotesApi(specialistSub).list() as Promise<SpecialistNote[]>
}

export async function createSpecialistNote(
  specialistSub: string,
  body: ThreadCommentCreate,
): Promise<SpecialistNote> {
  return specialistNotesApi(specialistSub).create(body) as Promise<SpecialistNote>
}

export async function uploadSpecialistNoteMedia(specialistSub: string, file: File): Promise<RichMediaRead> {
  return specialistNotesApi(specialistSub).uploadMedia(file)
}

export async function patchSpecialistNote(
  specialistSub: string,
  noteId: string,
  body: ThreadCommentUpdate,
): Promise<SpecialistNote> {
  return specialistNotesApi(specialistSub).update(noteId, body) as Promise<SpecialistNote>
}

export async function deleteSpecialistNote(specialistSub: string, noteId: string): Promise<void> {
  await specialistNotesApi(specialistSub).remove(noteId)
}

// ---------------------------------------------------------------------------
// Jira
// ---------------------------------------------------------------------------

export async function searchJiraSpecialists(q: string): Promise<JiraSearchHit[]> {
  const params = new URLSearchParams({ q })
  const res = await authenticatedFetch(`/portal/specialists/jira/search?${params}`)
  return parseJsonOrThrowApi(res)
}

export async function getSpecialistJira(specialistSub: string): Promise<SpecialistJiraState> {
  const res = await authenticatedFetch(`/portal/specialists/${encodeURIComponent(specialistSub)}/jira`)
  return parseJsonOrThrowApi(res)
}

export async function linkSpecialistJira(
  specialistSub: string,
  issueKey: string,
): Promise<SpecialistJiraState> {
  const res = await authenticatedFetch(`/portal/specialists/${encodeURIComponent(specialistSub)}/jira/link`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ issue_key: issueKey }),
  })
  return parseJsonOrThrowApi(res)
}

export async function syncSpecialistJira(specialistSub: string): Promise<SpecialistJiraState> {
  const res = await authenticatedFetch(`/portal/specialists/${encodeURIComponent(specialistSub)}/jira/sync`, {
    method: 'POST',
  })
  return parseJsonOrThrowApi(res)
}

export async function unlinkSpecialistJira(specialistSub: string): Promise<void> {
  const res = await authenticatedFetch(`/portal/specialists/${encodeURIComponent(specialistSub)}/jira/link`, {
    method: 'DELETE',
  })
  await parseJsonOrThrowApi<void>(res)
}

// ---------------------------------------------------------------------------
// Персональный порядок колонок канбана
// ---------------------------------------------------------------------------

export async function getSpecialistBoardPref(): Promise<SpecialistBoardPref> {
  const res = await authenticatedFetch('/portal/me/specialist-board-pref')
  return parseJsonOrThrowApi(res)
}

export async function putSpecialistBoardPref(
  body: SpecialistBoardPrefWrite,
): Promise<SpecialistBoardPref> {
  const res = await authenticatedFetch('/portal/me/specialist-board-pref', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return parseJsonOrThrowApi(res)
}
