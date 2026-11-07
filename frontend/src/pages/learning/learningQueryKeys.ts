import type { QueryClient } from '@tanstack/react-query'

/** Корень ключей обучения — инвалидация префиксом. */
export const LEARNING_ROOT_QUERY_KEY = ['portal', 'learning'] as const

/** Лимит списков на экране обучения (бэкенд le=500). */
export const LEARNING_LIST_LIMIT = 200

export const learningQueryKeys = {
  root: LEARNING_ROOT_QUERY_KEY,
  materialsRoot: [...LEARNING_ROOT_QUERY_KEY, 'materials'] as const,
  materials: (filters: { typeFilter: string; statusFilter: string; isPortalAdmin: boolean }) =>
    [...LEARNING_ROOT_QUERY_KEY, 'materials', filters] as const,
  checklists: [...LEARNING_ROOT_QUERY_KEY, 'checklists'] as const,
  checklistProgress: (checklistId: string) =>
    [...LEARNING_ROOT_QUERY_KEY, 'checklist-progress', checklistId] as const,
  quizzes: [...LEARNING_ROOT_QUERY_KEY, 'quizzes'] as const,
  quizEdit: (quizId: string) => [...LEARNING_ROOT_QUERY_KEY, 'quiz-edit', quizId] as const,
  /** Карточка теста для прохождения — тот же ключ, что инвалидируется после save редактора. */
  quizDetail: (quizId: string) => [...LEARNING_ROOT_QUERY_KEY, 'quiz', quizId] as const,
  quizAttempts: (quizId: string) => [...LEARNING_ROOT_QUERY_KEY, 'quiz-attempts', quizId] as const,
}

export function invalidateLearningQueries(
  queryClient: QueryClient,
  ...keys: ReadonlyArray<readonly unknown[]>
): void {
  for (const queryKey of keys) {
    void queryClient.invalidateQueries({ queryKey })
  }
}
