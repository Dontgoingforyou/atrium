import { useMemo, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import {
  deleteQuiz,
  replaceQuizQuestions,
  updateQuiz,
  type QuizQuestionWrite,
} from '../../api/learning/learningApi'
import { ConfirmDialog } from '../../components/ui/ConfirmDialog'
import { userFacingMessageFromUnknown } from '../../utils/apiUserMessage'
import {
  buildQuizQuestionsPayload,
  emptyDraftQuestion,
  newClientId,
  quizEditToDraft,
  type DraftQuestion,
} from './quizEditorUtils'
import { invalidateLearningQueries, learningQueryKeys } from './learningQueryKeys'
import styles from '@/styles/modules/learning/LearningPage.module.css'

export function QuizAdminEditorForm({
  quizId,
  initial,
  onClose,
}: {
  quizId: string
  initial: ReturnType<typeof quizEditToDraft>
  onClose: () => void
}) {
  const qc = useQueryClient()
  const [title, setTitle] = useState(initial.title)
  const [description, setDescription] = useState(initial.description)
  const [questions, setQuestions] = useState<DraftQuestion[]>(initial.questions)
  const [saveErr, setSaveErr] = useState<string | null>(null)
  const [pendingDelete, setPendingDelete] = useState(false)

  const updateMetaMut = useMutation({
    mutationFn: () =>
      updateQuiz(quizId, {
        title: title.trim(),
        description: description.trim() || null,
        material_id: initial.material_id.trim() || null,
      }),
    onError: (e) => setSaveErr(userFacingMessageFromUnknown(e)),
  })

  const replaceMut = useMutation({
    mutationFn: (payload: QuizQuestionWrite[]) => replaceQuizQuestions(quizId, payload),
    onError: (e) => setSaveErr(userFacingMessageFromUnknown(e)),
  })

  const delMut = useMutation({
    mutationFn: () => deleteQuiz(quizId),
    onSuccess: () => {
      invalidateLearningQueries(
        qc,
        learningQueryKeys.quizzes,
        learningQueryKeys.quizEdit(quizId),
        learningQueryKeys.quizDetail(quizId),
        learningQueryKeys.quizAttempts(quizId),
      )
      setPendingDelete(false)
      onClose()
    },
    onError: (e) => setSaveErr(userFacingMessageFromUnknown(e)),
  })

  const payload = useMemo(() => buildQuizQuestionsPayload(questions), [questions])

  function invalidateAfterSave() {
    invalidateLearningQueries(
      qc,
      learningQueryKeys.quizzes,
      learningQueryKeys.quizEdit(quizId),
      learningQueryKeys.quizDetail(quizId),
      learningQueryKeys.quizAttempts(quizId),
    )
  }

  async function saveAll() {
    setSaveErr(null)
    if (!title.trim()) {
      setSaveErr('Укажите название теста.')
      return
    }
    if (!payload) {
      setSaveErr('Каждый вопрос и ответ должны быть непустыми; у каждого вопроса ровно один верный ответ.')
      return
    }
    try {
      await updateMetaMut.mutateAsync()
    } catch {
      return
    }
    try {
      await replaceMut.mutateAsync(payload)
    } catch {
      return
    }
    invalidateAfterSave()
    onClose()
  }

  function setCorrectAnswer(qIdx: number, answerClientId: string) {
    setQuestions((prev) =>
      prev.map((q, i) => {
        if (i !== qIdx) return q
        return { ...q, answers: q.answers.map((a) => ({ ...a, is_correct: a.clientId === answerClientId })) }
      }),
    )
  }

  return (
    <div className={styles.adminForm}>
      <button type="button" className={styles.backBtn} onClick={onClose}>
        ← К списку
      </button>
      <h3 className={styles.adminFormTitle}>Редактирование теста</h3>
      <p className={`text-muted ${styles.adminHint}`}>
        Сохранение структуры удаляет все попытки прохождения этого теста.
      </p>
      {saveErr ? <p className="text-danger">{saveErr}</p> : null}

      <div className={styles.adminFieldStack}>
        <label className={styles.adminLabel}>
          Название
          <input className={styles.adminInput} value={title} onChange={(e) => setTitle(e.target.value)} />
        </label>
        <label className={styles.adminLabel}>
          Описание
          <textarea
            className={styles.adminTextarea}
            rows={2}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </label>
      </div>

      <h4 className={`${styles.adminFormTitle} ${styles.questionsHeading}`}>Вопросы и ответы</h4>
      <div className={styles.quizAdminBlock}>
        {questions.map((q, qIdx) => (
          <div key={q.clientId} className={styles.quizQuestionAdmin}>
            <label className={styles.adminLabel}>
              Вопрос {qIdx + 1}
              <input
                className={styles.adminInput}
                value={q.text}
                onChange={(e) => {
                  const v = e.target.value
                  setQuestions((prev) => prev.map((x, i) => (i === qIdx ? { ...x, text: v } : x)))
                }}
              />
            </label>
            <div className={styles.adminLabel}>Варианты (отметьте верный)</div>
            {q.answers.map((a) => (
              <div key={a.clientId} className={styles.checklistItemRow}>
                <input
                  type="radio"
                  name={`correct-${q.clientId}`}
                  checked={a.is_correct}
                  onChange={() => setCorrectAnswer(qIdx, a.clientId)}
                  aria-label="Верный ответ"
                  title="Верный ответ"
                />
                <input
                  value={a.text}
                  onChange={(e) => {
                    const v = e.target.value
                    setQuestions((prev) =>
                      prev.map((qq, i) => {
                        if (i !== qIdx) return qq
                        return {
                          ...qq,
                          answers: qq.answers.map((x) => (x.clientId === a.clientId ? { ...x, text: v } : x)),
                        }
                      }),
                    )
                  }}
                  placeholder="Текст ответа"
                />
                <button
                  type="button"
                  className="btn-secondary btn-sm"
                  aria-label="Удалить ответ"
                  onClick={() => {
                    setQuestions((prev) =>
                      prev.map((qq, i) => {
                        if (i !== qIdx) return qq
                        const next = qq.answers.filter((x) => x.clientId !== a.clientId)
                        if (next.length === 0) return qq
                        if (!next.some((x) => x.is_correct)) next[0] = { ...next[0], is_correct: true }
                        return { ...qq, answers: next }
                      }),
                    )
                  }}
                  disabled={q.answers.length <= 1}
                >
                  ✕
                </button>
              </div>
            ))}
            <button
              type="button"
              className="btn-secondary btn-sm"
              onClick={() => {
                setQuestions((prev) =>
                  prev.map((qq, i) => {
                    if (i !== qIdx) return qq
                    return {
                      ...qq,
                      answers: [...qq.answers, { clientId: newClientId(), text: '', is_correct: false }],
                    }
                  }),
                )
              }}
            >
              + Ответ
            </button>
            <button
              type="button"
              className={`btn-secondary btn-sm ${styles.deleteQuestionBtn}`}
              onClick={() => setQuestions((prev) => (prev.length <= 1 ? prev : prev.filter((_, i) => i !== qIdx)))}
              disabled={questions.length <= 1}
            >
              Удалить вопрос
            </button>
          </div>
        ))}
        <button
          type="button"
          className="btn-secondary btn-sm"
          onClick={() => setQuestions((prev) => [...prev, emptyDraftQuestion()])}
        >
          + Вопрос
        </button>
      </div>

      <div className={styles.adminFormActionsRow}>
        <button
          type="button"
          className="btn-primary"
          disabled={updateMetaMut.isPending || replaceMut.isPending}
          onClick={() => void saveAll()}
        >
          {updateMetaMut.isPending || replaceMut.isPending ? 'Сохранение…' : 'Сохранить'}
        </button>
        <button
          type="button"
          className="btn-secondary"
          disabled={delMut.isPending}
          onClick={() => setPendingDelete(true)}
        >
          {delMut.isPending ? 'Удаление…' : 'Удалить тест'}
        </button>
      </div>
      {pendingDelete ? (
        <ConfirmDialog
          open
          title="Удалить тест?"
          message="Удалить тест и все попытки?"
          confirmLabel="Удалить"
          cancelLabel="Отмена"
          destructive
          confirmSound="error"
          disabled={delMut.isPending}
          onConfirm={() => delMut.mutate()}
          onCancel={() => {
            if (!delMut.isPending) setPendingDelete(false)
          }}
        />
      ) : null}
    </div>
  )
}
