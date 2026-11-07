import type { QuizEdit, QuizQuestionWrite } from '../../types/learning'

export type DraftAnswer = { clientId: string; text: string; is_correct: boolean }
export type DraftQuestion = { clientId: string; text: string; answers: DraftAnswer[] }

export function newClientId(): string {
  return crypto.randomUUID()
}

export function emptyDraftQuestion(): DraftQuestion {
  return {
    clientId: newClientId(),
    text: '',
    answers: [
      { clientId: newClientId(), text: '', is_correct: true },
      { clientId: newClientId(), text: '', is_correct: false },
    ],
  }
}

export function quizEditToDraft(q: QuizEdit): {
  title: string
  description: string
  material_id: string
  questions: DraftQuestion[]
} {
  return {
    title: q.title,
    description: q.description ?? '',
    material_id: q.material_id ?? '',
    questions:
      q.questions.length > 0
        ? q.questions
            .slice()
            .sort((a, b) => a.order_index - b.order_index)
            .map((qq) => ({
              clientId: qq.id,
              text: qq.text,
              answers: qq.answers.map((a) => ({
                clientId: a.id,
                text: a.text,
                is_correct: a.is_correct,
              })),
            }))
        : [emptyDraftQuestion()],
  }
}

export function buildQuizQuestionsPayload(questions: DraftQuestion[]): QuizQuestionWrite[] | null {
  const out: QuizQuestionWrite[] = []
  for (const q of questions) {
    const qt = q.text.trim()
    if (!qt) return null
    const ans: { text: string; is_correct: boolean }[] = []
    let correct = 0
    for (const a of q.answers) {
      const t = a.text.trim()
      if (!t) return null
      ans.push({ text: t, is_correct: a.is_correct })
      if (a.is_correct) correct += 1
    }
    if (ans.length === 0 || correct !== 1) return null
    out.push({ text: qt, answers: ans })
  }
  return out
}
