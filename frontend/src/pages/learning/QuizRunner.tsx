import { useState, type KeyboardEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { getQuiz, startAttempt, submitAttempt } from '../../api/learning/learningApi'
import type { AttemptResult, Quiz, QuizAttemptStart } from '../../types/learning'
import { userFacingMessageFromUnknown } from '../../utils/apiUserMessage'
import styles from '@/styles/modules/learning/LearningPage.module.css'
import { invalidateLearningQueries, learningQueryKeys } from './learningQueryKeys'

type QuizPhase = 'start' | 'answering' | 'result'

export function QuizRunner({ quiz, onBack }: { quiz: Quiz; onBack: () => void }) {
  const queryClient = useQueryClient()
  const [phase, setPhase] = useState<QuizPhase>('start')
  const [attempt, setAttempt] = useState<QuizAttemptStart | null>(null)
  const [selected, setSelected] = useState<Record<string, string>>({})
  const [result, setResult] = useState<AttemptResult | null>(null)

  const { data: freshQuiz, isPending: quizLoading, isError, error } = useQuery({
    queryKey: learningQueryKeys.quizDetail(quiz.id),
    queryFn: () => getQuiz(quiz.id),
    initialData: quiz,
  })

  const runQuiz = freshQuiz ?? quiz

  const startMutation = useMutation({
    mutationFn: () => startAttempt(runQuiz.id),
    onSuccess: (data) => {
      setAttempt(data)
      setPhase('answering')
    },
  })

  const submitMutation = useMutation({
    mutationFn: () => {
      const answers = runQuiz.questions.map((q) => ({
        question_id: q.id,
        answer_id: selected[q.id] ?? null,
      }))
      return submitAttempt(runQuiz.id, attempt!.id, answers)
    },
    onSuccess: (data) => {
      setResult(data)
      setPhase('result')
      invalidateLearningQueries(queryClient, learningQueryKeys.quizAttempts(runQuiz.id))
    },
  })

  function selectAnswer(questionId: string, answerId: string) {
    setSelected((prev) => ({ ...prev, [questionId]: answerId }))
  }

  function onAnswerKeyDown(
    e: KeyboardEvent,
    questionId: string,
    answerIds: string[],
    answerId: string,
  ) {
    const current = selected[questionId] ?? answerIds[0]
    const idx = Math.max(0, answerIds.indexOf(current))
    if (e.key === 'ArrowDown' || e.key === 'ArrowRight') {
      e.preventDefault()
      selectAnswer(questionId, answerIds[(idx + 1) % answerIds.length])
    } else if (e.key === 'ArrowUp' || e.key === 'ArrowLeft') {
      e.preventDefault()
      selectAnswer(questionId, answerIds[(idx - 1 + answerIds.length) % answerIds.length])
    } else if (e.key === ' ' || e.key === 'Enter') {
      e.preventDefault()
      selectAnswer(questionId, answerId)
    }
  }

  if (quizLoading && !freshQuiz) {
    return <p className="text-muted">Загрузка…</p>
  }

  if (isError && !freshQuiz) {
    return <p className="text-danger">{userFacingMessageFromUnknown(error)}</p>
  }

  return (
    <div className={styles.quizPage}>
      <button type="button" className={styles.backBtn} onClick={onBack}>
        ← К списку тестов
      </button>
      <h2 className={styles.quizPageTitle}>{runQuiz.title}</h2>

      {phase === 'start' && (
        <div>
          {runQuiz.description && (
            <p className={`text-muted ${styles.quizStartDesc}`}>{runQuiz.description}</p>
          )}
          <p className={styles.quizQuestionCount}>
            Вопросов: <b>{runQuiz.questions.length}</b>
          </p>
          <button
            type="button"
            className="btn-primary"
            onClick={() => startMutation.mutate()}
            disabled={startMutation.isPending}
          >
            {startMutation.isPending ? 'Начинаем…' : 'Начать тест'}
          </button>
          {startMutation.isError && (
            <p className="text-danger">{userFacingMessageFromUnknown(startMutation.error)}</p>
          )}
        </div>
      )}

      {phase === 'answering' && (
        <div>
          {runQuiz.questions.map((q, idx) => {
            const answerIds = q.answers.map((a) => a.id)
            return (
              <div key={q.id} className={styles.questionBlock}>
                <div className={styles.questionText} id={`quiz-q-${q.id}`}>
                  {idx + 1}. {q.text}
                </div>
                <div
                  className={styles.answerOptions}
                  role="radiogroup"
                  aria-labelledby={`quiz-q-${q.id}`}
                >
                  {q.answers.map((a, aIdx) => {
                    const isSelected = selected[q.id] === a.id
                    const tabbable = isSelected || (!selected[q.id] && aIdx === 0)
                    return (
                      <div
                        key={a.id}
                        className={`${styles.answerOption} ${isSelected ? styles.answerOptionSelected : ''}`}
                        role="radio"
                        aria-checked={isSelected}
                        tabIndex={tabbable ? 0 : -1}
                        onClick={() => selectAnswer(q.id, a.id)}
                        onKeyDown={(e) => onAnswerKeyDown(e, q.id, answerIds, a.id)}
                      >
                        <span className={styles.answerOptionText}>{a.text}</span>
                      </div>
                    )
                  })}
                </div>
              </div>
            )
          })}
          <button
            type="button"
            className={`btn-primary ${styles.submitBtn}`}
            onClick={() => submitMutation.mutate()}
            disabled={submitMutation.isPending}
          >
            {submitMutation.isPending ? 'Отправка…' : 'Завершить тест'}
          </button>
          {submitMutation.isError && (
            <p className="text-danger">{userFacingMessageFromUnknown(submitMutation.error)}</p>
          )}
        </div>
      )}

      {phase === 'result' && result && (
        <div>
          <div className={styles.resultBlock}>
            <div className={styles.resultScore}>
              {result.score} / {result.max_score}
            </div>
            <div className={styles.resultLabel}>
              {result.max_score > 0
                ? `${Math.round((result.score / result.max_score) * 100)}% правильных ответов`
                : 'Результат'}
            </div>
          </div>

          {result.answers.map((qa, idx) => {
            const correctAnswer = qa.answers.find((a) => a.is_correct)
            const userAnswer = qa.answers.find((a) => a.id === qa.selected_answer_id)
            const isCorrect = userAnswer?.is_correct ?? false

            return (
              <div key={qa.question_id} className={styles.questionBlock}>
                <div className={styles.questionText}>
                  {idx + 1}. {qa.question_text}
                </div>
                <div className={styles.answerOptions}>
                  {qa.answers.map((a) => {
                    let cls = styles.answerOption
                    if (a.id === qa.selected_answer_id) {
                      cls += ` ${a.is_correct ? styles.answerOptionCorrect : styles.answerOptionWrong}`
                    } else if (a.is_correct) {
                      cls += ` ${styles.answerOptionCorrect}`
                    }
                    return (
                      <div key={a.id} className={cls}>
                        <span className={styles.answerOptionText}>{a.text}</span>
                        {a.is_correct && <span className={styles.correctMark}>✓ правильный</span>}
                      </div>
                    )
                  })}
                </div>
                {!isCorrect && correctAnswer && (
                  <p className={styles.wrongHint}>Правильный ответ: «{correctAnswer.text}»</p>
                )}
              </div>
            )
          })}

          <button type="button" className={`btn-secondary ${styles.submitBtn}`} onClick={onBack}>
            Вернуться к тестам
          </button>
        </div>
      )}
    </div>
  )
}
