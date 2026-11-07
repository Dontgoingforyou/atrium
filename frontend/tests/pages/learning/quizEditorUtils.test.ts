import { describe, expect, it } from 'vitest'
import type { QuizEdit } from '../../../src/types/learning'
import { isChecklistProgressAbsentError } from '../../../src/pages/learning/checklistProgressError'
import {
  LEARNING_LIST_LIMIT,
  LEARNING_ROOT_QUERY_KEY,
  learningQueryKeys,
} from '../../../src/pages/learning/learningQueryKeys'
import {
  buildQuizQuestionsPayload,
  quizEditToDraft,
  type DraftQuestion,
} from '../../../src/pages/learning/quizEditorUtils'

function draftQuestion(over: Partial<DraftQuestion> & Pick<DraftQuestion, 'answers'>): DraftQuestion {
  return {
    clientId: over.clientId ?? 'q1',
    text: over.text ?? 'Вопрос',
    answers: over.answers,
  }
}

describe('learningQueryKeys', () => {
  it('все ключи начинаются с LEARNING_ROOT_QUERY_KEY', () => {
    expect(learningQueryKeys.materialsRoot.slice(0, 2)).toEqual([...LEARNING_ROOT_QUERY_KEY])
    expect(learningQueryKeys.quizDetail('quiz-1')[2]).toBe('quiz')
    expect(learningQueryKeys.quizAttempts('quiz-1')[2]).toBe('quiz-attempts')
    expect(LEARNING_LIST_LIMIT).toBe(200)
  })
})

describe('quizEditToDraft', () => {
  it('сортирует вопросы по order_index', () => {
    const quiz: QuizEdit = {
      id: 'quiz-1',
      title: 'Тест',
      description: null,
      material_id: null,
      created_at: '',
      updated_at: '',
      questions: [
        {
          id: 'q-b',
          quiz_id: 'quiz-1',
          text: 'Второй',
          order_index: 2,
          answers: [{ id: 'a1', question_id: 'q-b', text: 'A', is_correct: true }],
        },
        {
          id: 'q-a',
          quiz_id: 'quiz-1',
          text: 'Первый',
          order_index: 1,
          answers: [{ id: 'a2', question_id: 'q-a', text: 'B', is_correct: true }],
        },
      ],
    }
    expect(quizEditToDraft(quiz).questions.map((q) => q.text)).toEqual(['Первый', 'Второй'])
  })
})

describe('buildQuizQuestionsPayload', () => {
  it('собирает payload при ровно одном верном ответе', () => {
    const payload = buildQuizQuestionsPayload([
      draftQuestion({
        text: 'Столица?',
        answers: [
          { clientId: 'a1', text: 'Москва', is_correct: true },
          { clientId: 'a2', text: 'Казань', is_correct: false },
        ],
      }),
    ])
    expect(payload).toEqual([
      {
        text: 'Столица?',
        answers: [
          { text: 'Москва', is_correct: true },
          { text: 'Казань', is_correct: false },
        ],
      },
    ])
  })

  it('возвращает null при пустом тексте или не ровно одном верном', () => {
    expect(
      buildQuizQuestionsPayload([
        draftQuestion({
          text: '  ',
          answers: [
            { clientId: 'a1', text: 'A', is_correct: true },
            { clientId: 'a2', text: 'B', is_correct: false },
          ],
        }),
      ]),
    ).toBeNull()
    expect(
      buildQuizQuestionsPayload([
        draftQuestion({
          answers: [
            { clientId: 'a1', text: 'A', is_correct: true },
            { clientId: 'a2', text: 'B', is_correct: true },
          ],
        }),
      ]),
    ).toBeNull()
    expect(
      buildQuizQuestionsPayload([
        draftQuestion({
          answers: [
            { clientId: 'a1', text: 'A', is_correct: false },
            { clientId: 'a2', text: 'B', is_correct: false },
          ],
        }),
      ]),
    ).toBeNull()
  })
})

describe('isChecklistProgressAbsentError', () => {
  it('распознаёт 404 «прохождение не найдено» и отвергает прочие ошибки', () => {
    expect(
      isChecklistProgressAbsentError(new Error('Прохождение не найдено. Сначала начните чек-лист.')),
    ).toBe(true)
    expect(isChecklistProgressAbsentError(new Error('Сервис временно недоступен. Попробуйте позже.'))).toBe(
      false,
    )
    expect(isChecklistProgressAbsentError(new Error('Не удалось связаться с сервером. Проверьте сеть.'))).toBe(
      false,
    )
  })
})
