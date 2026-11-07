import { useQuery } from '@tanstack/react-query'
import { getQuizForEdit } from '../../api/learning/learningApi'
import { userFacingMessageFromUnknown } from '../../utils/apiUserMessage'
import { QuizAdminEditorForm } from './QuizAdminEditorForm'
import { quizEditToDraft } from './quizEditorUtils'
import { learningQueryKeys } from './learningQueryKeys'

export function QuizAdminEditor({ quizId, onClose }: { quizId: string; onClose: () => void }) {
  const { data, isPending, isError, error } = useQuery({
    queryKey: learningQueryKeys.quizEdit(quizId),
    queryFn: () => getQuizForEdit(quizId),
  })

  if (isPending) return <p className="text-muted">Загрузка редактора…</p>
  if (isError) return <p className="text-danger">{userFacingMessageFromUnknown(error)}</p>
  if (!data) return <p className="text-muted">Нет данных.</p>

  const initial = quizEditToDraft(data)
  return (
    <QuizAdminEditorForm
      key={`${quizId}-${data.updated_at}`}
      quizId={quizId}
      initial={initial}
      onClose={onClose}
    />
  )
}
