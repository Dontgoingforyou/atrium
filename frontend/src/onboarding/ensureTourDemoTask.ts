import { listTags } from '../api/tags/tagsApi'
import { createTask, deleteTask, listTasks } from '../api/tasks/tasksApi'
import type { TaskPriority } from '../types/task'
import { warnTourCleanupError } from './tourCleanupLog'

/** Отображаемый заголовок учебной задачи (не участвует в RBAC удаления). */
export const TOUR_DEMO_TASK_TITLE = 'Учебная задача'

export const TOUR_DEMO_TASK_DESCRIPTION =
  '<p>Это учебная задача для онбординга. Здесь описание: можно форматировать текст, вставлять списки и ссылки.</p>'

export const TOUR_DEMO_TASK_PRIORITY: TaskPriority = 'medium'

export type TourDemoTaskPrefill = {
  title: string
  description: string
  priority: TaskPriority
  dueDate: string
  tagIds: string[]
  assigneeSubs: string[]
  suppressAutoCreate: true
}

export type EnsureTourDemoTaskResult =
  | { ok: true; created: boolean; taskId: string; prefill: TourDemoTaskPrefill }
  | { ok: false; reason: string }

function dueDatePlusDays(days: number): string {
  const d = new Date()
  d.setUTCDate(d.getUTCDate() + days)
  return d.toISOString().slice(0, 10)
}

export function buildTourDemoTaskPrefill(
  currentUserSub: string,
  tagIds: string[] = [],
): TourDemoTaskPrefill {
  return {
    title: TOUR_DEMO_TASK_TITLE,
    description: TOUR_DEMO_TASK_DESCRIPTION,
    priority: TOUR_DEMO_TASK_PRIORITY,
    dueDate: dueDatePlusDays(7),
    tagIds,
    assigneeSubs: [currentUserSub],
    suppressAutoCreate: true,
  }
}

export async function ensureGuidedTourDemoTask(
  currentUserSub: string,
): Promise<EnsureTourDemoTaskResult> {
  if (!currentUserSub) {
    return { ok: false, reason: 'Не удалось подготовить учебную задачу: пользователь не определён.' }
  }

  const existing = await listTasks({ mine_only: true, limit: 100 })
  const found = existing.find((t) => t.is_tour_demo)
  if (found) {
    const tagIds = found.tags.map((t) => t.id)
    return {
      ok: true,
      created: false,
      taskId: found.id,
      prefill: {
        ...buildTourDemoTaskPrefill(currentUserSub, tagIds),
        description: found.description || TOUR_DEMO_TASK_DESCRIPTION,
        priority: found.priority,
        dueDate: found.due_at ? found.due_at.slice(0, 10) : dueDatePlusDays(7),
      },
    }
  }

  let tagIds: string[] = []
  try {
    const tags = await listTags()
    if (tags[0]) tagIds = [tags[0].id]
  } catch {
    tagIds = []
  }

  const prefill = buildTourDemoTaskPrefill(currentUserSub, tagIds)
  const created = await createTask({
    title: prefill.title,
    description: prefill.description,
    priority: prefill.priority,
    assignee_subs: prefill.assigneeSubs,
    due_at: prefill.dueDate,
    is_tour_demo: true,
    ...(tagIds.length > 0 ? { tag_ids: tagIds } : {}),
  })

  return { ok: true, created: true, taskId: created.id, prefill }
}

/** Удаляет учебную задачу; 404 не считается ошибкой. */
export async function cleanupGuidedTourDemoTask(taskId: string): Promise<void> {
  try {
    await deleteTask(taskId)
  } catch (e) {
    warnTourCleanupError('demo task', e)
  }
}

export {
  stepNeedsTourCreateFormPage,
  stepNeedsTourDemoTask,
  stepNeedsTourTaskDetailPage,
  tourTaskDetailAnchorForStep,
} from '../domain/onboarding/guidedTour'

/** Событие: развернуть секцию карточки задачи для spotlight тура. */
export const GUIDED_TOUR_TASK_PANEL_EVENT = 'guided-tour-task-panel'

export type GuidedTourTaskPanelDetail = {
  /** Значение data-tour на TaskDetailPanel. */
  tourAnchor: string
}

export function dispatchGuidedTourTaskPanel(tourAnchor: string): void {
  if (typeof document === 'undefined') return
  document.dispatchEvent(
    new CustomEvent<GuidedTourTaskPanelDetail>(GUIDED_TOUR_TASK_PANEL_EVENT, {
      detail: { tourAnchor },
    }),
  )
}
