import type { ManagerSpecialistEntry } from '../../types/specialist'
import { SpecialistKanbanCardContent } from './SpecialistKanbanCardContent'
import taskStyles from '@/styles/modules/tasks/TasksPageKanbanCards.module.css'

/** Неинтерактивная копия карточки, которая следует за указателем при drag-and-drop. */
export function SpecialistKanbanDragOverlay({
  entry,
}: {
  entry: ManagerSpecialistEntry
}) {
  return (
    <div className={`${taskStyles.kanbanCard} ${taskStyles.kanbanDragOverlayCard}`}>
      <SpecialistKanbanCardContent entry={entry} />
    </div>
  )
}
