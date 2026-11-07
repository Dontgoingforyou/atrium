export type MaterialType = 'article' | 'video' | 'presentation' | 'instruction'
export type MaterialStatus = 'draft' | 'active' | 'archived'
export type UserChecklistStatus = 'in_progress' | 'completed'

export interface LearningMaterial {
  id: string
  title: string
  body: string | null
  material_type: MaterialType
  status: MaterialStatus
  idp_groups: string[]
  created_by_sub: string
  /** Версия для CAS (optimistic locking). */
  version: number
  created_at: string
  updated_at: string
}

export interface ChecklistItem {
  id: string
  checklist_id: string
  order_index: number
  text: string
}

export interface Checklist {
  id: string
  title: string
  description: string | null
  idp_group: string
  /** Версия для CAS (optimistic locking). */
  version: number
  created_at: string
  updated_at: string
  items: ChecklistItem[]
}

export interface UserChecklistItemMark {
  id: string
  user_checklist_id: string
  item_id: string
  is_done: boolean
  done_at: string | null
}

export interface UserChecklistProgress {
  id: string
  user_sub: string
  checklist_id: string
  status: UserChecklistStatus
  started_at: string
  completed_at: string | null
  item_marks: UserChecklistItemMark[]
  checklist: Checklist | null
}

export interface QuizAnswer {
  id: string
  question_id: string
  text: string
}

/** Ответ с признаком верности — только эндпоинт for-edit для админа. */
export interface QuizAnswerEdit extends QuizAnswer {
  is_correct: boolean
}

export interface QuizQuestionEdit {
  id: string
  quiz_id: string
  text: string
  order_index: number
  answers: QuizAnswerEdit[]
}

export interface QuizEdit {
  id: string
  title: string
  description: string | null
  material_id: string | null
  created_at: string
  updated_at: string
  questions: QuizQuestionEdit[]
}

export interface QuizAnswerWithCorrect extends QuizAnswer {
  is_correct: boolean
}

export interface QuizQuestion {
  id: string
  quiz_id: string
  text: string
  order_index: number
  answers: QuizAnswer[]
}

export interface Quiz {
  id: string
  title: string
  description: string | null
  material_id: string | null
  created_at: string
  updated_at: string
  questions: QuizQuestion[]
}

export interface QuizAttemptStart {
  id: string
  quiz_id: string
  user_sub: string
  score: number
  max_score: number
  started_at: string
  finished_at: string | null
}

export interface AttemptAnswerResult {
  question_id: string
  question_text: string
  selected_answer_id: string | null
  answers: QuizAnswerWithCorrect[]
}

export interface AttemptResult {
  id: string
  quiz_id: string
  user_sub: string
  score: number
  max_score: number
  started_at: string
  finished_at: string | null
  answers: AttemptAnswerResult[]
}

export interface AttemptHistory {
  id: string
  quiz_id: string
  user_sub: string
  score: number
  max_score: number
  started_at: string
  finished_at: string | null
}

// --- Write-DTO (create/update) ---

export type LearningMaterialCreateBody = {
  title: string
  body?: string | null
  material_type?: MaterialType
  status?: MaterialStatus
  idp_groups?: string[]
}

export type LearningMaterialUpdateBody = {
  expected_version: number
} & Partial<LearningMaterialCreateBody>

export type ChecklistCreateBody = {
  title: string
  description?: string | null
  idp_group?: string
  items?: string[]
}

export type ChecklistUpdateBody = {
  expected_version: number
  title?: string
  description?: string | null
  idp_group?: string | null
  /** Полная замена пунктов; сбрасывает прогресс пользователей. */
  items?: string[] | null
}

export type QuizCreateBody = {
  title: string
  description?: string | null
  material_id?: string | null
}

export type QuizUpdateBody = Partial<QuizCreateBody>

export type QuizAnswerWrite = { text: string; is_correct?: boolean }
export type QuizQuestionWrite = { text: string; answers: QuizAnswerWrite[] }
