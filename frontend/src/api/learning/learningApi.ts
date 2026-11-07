import type {
  AttemptHistory,
  AttemptResult,
  Checklist,
  ChecklistCreateBody,
  ChecklistUpdateBody,
  LearningMaterial,
  LearningMaterialCreateBody,
  LearningMaterialUpdateBody,
  Quiz,
  QuizAttemptStart,
  QuizCreateBody,
  QuizEdit,
  QuizQuestionWrite,
  QuizUpdateBody,
  UserChecklistProgress,
} from '../../types/learning'
import { parseJsonOrThrowApi } from '../parseResponse'
import { authenticatedFetch } from '../rawClient'

// Реэкспорт write-DTO для совместимости с существующими импортами из api/learning.
export type {
  ChecklistCreateBody,
  ChecklistUpdateBody,
  LearningMaterialCreateBody,
  LearningMaterialUpdateBody,
  QuizCreateBody,
  QuizQuestionWrite,
  QuizUpdateBody,
}

const BASE = '/portal/learning'

// ── Материалы ──────────────────────────────────────────────────────────────

export async function listMaterials(params?: {
  material_type?: string
  status?: string
  limit?: number
  offset?: number
}): Promise<LearningMaterial[]> {
  const qs = new URLSearchParams()
  if (params?.material_type) qs.set('material_type', params.material_type)
  if (params?.status) qs.set('status', params.status)
  if (params?.limit !== undefined) qs.set('limit', String(params.limit))
  if (params?.offset !== undefined) qs.set('offset', String(params.offset))
  const query = qs.toString() ? `?${qs}` : ''
  const res = await authenticatedFetch(`${BASE}/materials${query}`)
  return parseJsonOrThrowApi(res)
}

export async function getMaterial(id: string): Promise<LearningMaterial> {
  const res = await authenticatedFetch(`${BASE}/materials/${id}`)
  return parseJsonOrThrowApi(res)
}

export async function createMaterial(body: LearningMaterialCreateBody): Promise<LearningMaterial> {
  const res = await authenticatedFetch(`${BASE}/materials`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return parseJsonOrThrowApi(res)
}

export async function updateMaterial(
  id: string,
  body: LearningMaterialUpdateBody,
): Promise<LearningMaterial> {
  const res = await authenticatedFetch(`${BASE}/materials/${encodeURIComponent(id)}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return parseJsonOrThrowApi(res)
}

export async function deleteMaterial(id: string): Promise<void> {
  const res = await authenticatedFetch(`${BASE}/materials/${encodeURIComponent(id)}`, {
    method: 'DELETE',
  })
  await parseJsonOrThrowApi(res)
}

// ── Чек-листы ──────────────────────────────────────────────────────────────

export async function listChecklists(params?: {
  limit?: number
  offset?: number
}): Promise<Checklist[]> {
  const qs = new URLSearchParams()
  if (params?.limit !== undefined) qs.set('limit', String(params.limit))
  if (params?.offset !== undefined) qs.set('offset', String(params.offset))
  const query = qs.toString() ? `?${qs}` : ''
  const res = await authenticatedFetch(`${BASE}/checklists${query}`)
  return parseJsonOrThrowApi(res)
}

export async function startChecklist(checklistId: string): Promise<UserChecklistProgress> {
  const res = await authenticatedFetch(`${BASE}/checklists/${checklistId}/start`, { method: 'POST' })
  return parseJsonOrThrowApi(res)
}

export async function getMyProgress(checklistId: string): Promise<UserChecklistProgress> {
  const res = await authenticatedFetch(`${BASE}/checklists/${checklistId}/my-progress`)
  return parseJsonOrThrowApi(res)
}

export async function markChecklistItem(
  checklistId: string,
  itemId: string,
  isDone: boolean,
): Promise<UserChecklistProgress> {
  const res = await authenticatedFetch(`${BASE}/checklists/${checklistId}/items/${itemId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ is_done: isDone }),
  })
  return parseJsonOrThrowApi(res)
}

export async function createChecklist(body: ChecklistCreateBody): Promise<Checklist> {
  const res = await authenticatedFetch(`${BASE}/checklists`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return parseJsonOrThrowApi(res)
}

export async function updateChecklist(id: string, body: ChecklistUpdateBody): Promise<Checklist> {
  const res = await authenticatedFetch(`${BASE}/checklists/${encodeURIComponent(id)}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return parseJsonOrThrowApi(res)
}

export async function deleteChecklist(id: string): Promise<void> {
  const res = await authenticatedFetch(`${BASE}/checklists/${encodeURIComponent(id)}`, {
    method: 'DELETE',
  })
  return parseJsonOrThrowApi(res)
}

// ── Тесты ──────────────────────────────────────────────────────────────────

export async function listQuizzes(params?: {
  limit?: number
  offset?: number
}): Promise<Quiz[]> {
  const qs = new URLSearchParams()
  if (params?.limit !== undefined) qs.set('limit', String(params.limit))
  if (params?.offset !== undefined) qs.set('offset', String(params.offset))
  const query = qs.toString() ? `?${qs}` : ''
  const res = await authenticatedFetch(`${BASE}/quizzes${query}`)
  return parseJsonOrThrowApi(res)
}

export async function getQuiz(id: string): Promise<Quiz> {
  const res = await authenticatedFetch(`${BASE}/quizzes/${id}`)
  return parseJsonOrThrowApi(res)
}

export async function getQuizForEdit(id: string): Promise<QuizEdit> {
  const res = await authenticatedFetch(`${BASE}/quizzes/${encodeURIComponent(id)}/for-edit`)
  return parseJsonOrThrowApi(res)
}

export async function createQuiz(body: QuizCreateBody): Promise<Quiz> {
  const res = await authenticatedFetch(`${BASE}/quizzes`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return parseJsonOrThrowApi(res)
}

export async function updateQuiz(id: string, body: QuizUpdateBody): Promise<Quiz> {
  const res = await authenticatedFetch(`${BASE}/quizzes/${encodeURIComponent(id)}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return parseJsonOrThrowApi(res)
}

export async function replaceQuizQuestions(
  quizId: string,
  questions: QuizQuestionWrite[],
): Promise<Quiz> {
  const res = await authenticatedFetch(`${BASE}/quizzes/${encodeURIComponent(quizId)}/questions`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ questions }),
  })
  return parseJsonOrThrowApi(res)
}

export async function deleteQuiz(id: string): Promise<void> {
  const res = await authenticatedFetch(`${BASE}/quizzes/${encodeURIComponent(id)}`, {
    method: 'DELETE',
  })
  return parseJsonOrThrowApi(res)
}

export async function startAttempt(quizId: string): Promise<QuizAttemptStart> {
  const res = await authenticatedFetch(`${BASE}/quizzes/${quizId}/attempts`, { method: 'POST' })
  return parseJsonOrThrowApi(res)
}

export async function submitAttempt(
  quizId: string,
  attemptId: string,
  answers: { question_id: string; answer_id: string | null }[],
): Promise<AttemptResult> {
  const res = await authenticatedFetch(`${BASE}/quizzes/${quizId}/attempts/${attemptId}/submit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ answers }),
  })
  return parseJsonOrThrowApi(res)
}

export async function listMyAttempts(quizId: string): Promise<AttemptHistory[]> {
  const res = await authenticatedFetch(`${BASE}/quizzes/${quizId}/attempts`)
  return parseJsonOrThrowApi(res)
}
