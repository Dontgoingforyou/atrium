import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { createQuiz, deleteQuiz, listMyAttempts, listQuizzes } from '../../api/learning/learningApi'
import { ConfirmDialog } from '../../components/ui/ConfirmDialog'
import { useNotifyToast } from '../../hooks/useNotifyToast'
import { useAuthStore } from '../../store/authStore'
import type { Quiz } from '../../types/learning'
import { userFacingMessageFromUnknown } from '../../utils/apiUserMessage'
import styles from '@/styles/modules/learning/LearningPage.module.css'
import { QuizAdminEditor } from './QuizAdminEditor'
import { QuizRunner } from './QuizRunner'
import {
  LEARNING_LIST_LIMIT,
  invalidateLearningQueries,
  learningQueryKeys,
} from './learningQueryKeys'

export function QuizzesTab() {
  const isPortalAdmin = useAuthStore((s) => s.user?.is_portal_admin ?? false)
  const notifyToast = useNotifyToast()
  const qc = useQueryClient()
  const [creating, setCreating] = useState(false)
  const [adminQuizId, setAdminQuizId] = useState<string | null>(null)
  const [selectedQuiz, setSelectedQuiz] = useState<Quiz | null>(null)
  const [pendingDelete, setPendingDelete] = useState<{ id: string; title: string } | null>(null)

  const listQuizDeleteMut = useMutation({
    mutationFn: (id: string) => deleteQuiz(id),
    onSuccess: () => {
      invalidateLearningQueries(qc, learningQueryKeys.quizzes)
      setPendingDelete(null)
    },
    onError: (e) => notifyToast(userFacingMessageFromUnknown(e), { silent: true }),
  })

  const { data, isPending, isError, error } = useQuery({
    queryKey: learningQueryKeys.quizzes,
    queryFn: () => listQuizzes({ limit: LEARNING_LIST_LIMIT }),
  })

  if (creating) {
    return (
      <QuizCreateTitleForm
        onCancel={() => setCreating(false)}
        onCreated={(id) => {
          setCreating(false)
          setAdminQuizId(id)
        }}
      />
    )
  }

  if (adminQuizId) {
    return <QuizAdminEditor quizId={adminQuizId} onClose={() => setAdminQuizId(null)} />
  }

  if (selectedQuiz) {
    return <QuizRunner quiz={selectedQuiz} onBack={() => setSelectedQuiz(null)} />
  }

  if (isPending) return <p className="text-muted">Загрузка…</p>
  if (isError) return <p className="text-danger">{userFacingMessageFromUnknown(error)}</p>

  return (
    <div>
      {isPortalAdmin ? (
        <div className={styles.adminToolbar}>
          <button type="button" className="btn-primary btn-sm" onClick={() => setCreating(true)}>
            + Новый тест
          </button>
        </div>
      ) : null}

      {!data || data.length === 0 ? (
        <p className="text-muted">Тестов нет</p>
      ) : (
        <div className={styles.quizList}>
          {data.map((quiz) => (
            <div key={quiz.id} className={styles.quizCard}>
              <div className={styles.quizCardHeader}>
                <span className={styles.quizTitle}>{quiz.title}</span>
                <div className={styles.quizCardActions}>
                  {isPortalAdmin ? (
                    <button type="button" className="btn-secondary btn-sm" onClick={() => setAdminQuizId(quiz.id)}>
                      Редактировать
                    </button>
                  ) : null}
                  {isPortalAdmin ? (
                    <button
                      type="button"
                      className="btn-secondary btn-sm"
                      disabled={listQuizDeleteMut.isPending}
                      onClick={() => setPendingDelete({ id: quiz.id, title: quiz.title })}
                    >
                      Удалить
                    </button>
                  ) : null}
                  <button type="button" className="btn-primary" onClick={() => setSelectedQuiz(quiz)}>
                    Пройти
                  </button>
                </div>
              </div>
              {quiz.description && <p className={styles.quizMeta}>{quiz.description}</p>}
              <QuizAttemptsHistory quizId={quiz.id} />
            </div>
          ))}
        </div>
      )}

      {pendingDelete ? (
        <ConfirmDialog
          open
          title="Удалить тест?"
          message={`Удалить тест «${pendingDelete.title}» и все попытки?`}
          confirmLabel="Удалить"
          cancelLabel="Отмена"
          destructive
          confirmSound="error"
          disabled={listQuizDeleteMut.isPending}
          onConfirm={() => listQuizDeleteMut.mutate(pendingDelete.id)}
          onCancel={() => {
            if (!listQuizDeleteMut.isPending) setPendingDelete(null)
          }}
        />
      ) : null}
    </div>
  )
}

function QuizCreateTitleForm({
  onCancel,
  onCreated,
}: {
  onCancel: () => void
  onCreated: (id: string) => void
}) {
  const qc = useQueryClient()
  const [title, setTitle] = useState('')
  const [err, setErr] = useState<string | null>(null)
  const mut = useMutation({
    mutationFn: () => createQuiz({ title: title.trim() }),
    onSuccess: (q) => {
      setErr(null)
      invalidateLearningQueries(qc, learningQueryKeys.quizzes)
      onCreated(q.id)
    },
    onError: (e) => setErr(userFacingMessageFromUnknown(e)),
  })

  return (
    <div className={styles.adminForm}>
      <button type="button" className={styles.backBtn} onClick={onCancel}>
        ← Отмена
      </button>
      <h3 className={styles.adminFormTitle}>Новый тест</h3>
      {err ? <p className="text-danger">{err}</p> : null}
      <label className={styles.adminLabel}>
        Название
        <input className={styles.adminInput} value={title} onChange={(e) => setTitle(e.target.value)} />
      </label>
      <div className={styles.adminFormActions}>
        <button
          type="button"
          className="btn-primary"
          disabled={!title.trim() || mut.isPending}
          onClick={() => mut.mutate()}
        >
          {mut.isPending ? 'Создание…' : 'Далее: структура'}
        </button>
      </div>
    </div>
  )
}

function QuizAttemptsHistory({ quizId }: { quizId: string }) {
  const { data, isError, error } = useQuery({
    queryKey: learningQueryKeys.quizAttempts(quizId),
    queryFn: () => listMyAttempts(quizId),
  })

  if (isError) {
    return <p className="text-danger">{userFacingMessageFromUnknown(error)}</p>
  }

  if (!data || data.length === 0) return null

  const finished = data.filter((a) => a.finished_at !== null)
  if (finished.length === 0) return null

  return (
    <div className={styles.attemptsWrap}>
      <div className={styles.attemptsCaption}>История попыток:</div>
      <table className={styles.attemptsTable}>
        <thead>
          <tr>
            <th>Дата</th>
            <th>Результат</th>
          </tr>
        </thead>
        <tbody>
          {finished.slice(0, 5).map((a) => (
            <tr key={a.id}>
              <td>{new Date(a.started_at).toLocaleDateString('ru-RU')}</td>
              <td>
                {a.score} / {a.max_score}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
