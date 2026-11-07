import type { CSSProperties } from 'react'
import { useSortable } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'

import type { ManagerSpecialistEntry, SpecialistColumn } from '../../types/specialist'
import taskStyles from '@/styles/modules/tasks/TasksPageKanbanCards.module.css'
import styles from '@/styles/modules/specialists/SpecialistsPage.module.css'
import { SpecialistKanbanCardContent } from './SpecialistKanbanCardContent'

interface Props {
  entry: ManagerSpecialistEntry
  columns: SpecialistColumn[]
  readOnly?: boolean
  sortable?: boolean
  onRemove: (specialistSub: string) => void
  onColumnChange?: (specialistSub: string, columnKey: string) => void
  columnChanging?: boolean
  onCardClick?: (entry: ManagerSpecialistEntry) => void
  isTourAnchor?: boolean
}

export function SpecialistKanbanCard({
  entry,
  columns,
  readOnly = false,
  sortable = false,
  onRemove,
  onColumnChange,
  columnChanging = false,
  onCardClick,
  isTourAnchor = false,
}: Props) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: entry.id,
    disabled: !sortable || readOnly,
    data: { type: 'specialist-entry', entry },
  })

  function handleDragStart(e: React.DragEvent<HTMLDivElement>) {
    if (readOnly) {
      e.preventDefault()
      return
    }
    e.dataTransfer.setData('specialist-sub', entry.specialist_sub)
    e.dataTransfer.effectAllowed = 'move'
  }

  return (
    <div
      ref={setNodeRef}
      draggable={!sortable && !readOnly}
      onDragStart={handleDragStart}
      data-kanban-card
      data-specialist-entry-id={entry.id}
      {...(isTourAnchor ? { 'data-tour': 'specialists-kanban-card' as const } : {})}
      className={`${taskStyles.kanbanCard} ${onCardClick ? styles.cardClickable : ''} ${
        sortable && !readOnly ? (isDragging ? styles.cardDragging : styles.cardSortable) : ''
      }`}
      style={{
        transform: transform ? CSS.Transform.toString(transform) : undefined,
        transition,
        opacity: isDragging ? 0 : 1,
      } as CSSProperties}
      {...(sortable && !readOnly ? listeners : {})}
      {...(sortable && !readOnly ? attributes : {})}
      onClick={onCardClick && !isDragging ? () => onCardClick(entry) : undefined}
    >
      <SpecialistKanbanCardContent
        entry={entry}
        columns={columns}
        showRemove={!readOnly}
        onRemove={onRemove}
        canChangeColumn={!readOnly && Boolean(onColumnChange)}
        columnChanging={columnChanging}
        onColumnChange={
          onColumnChange ? (columnKey) => onColumnChange(entry.specialist_sub, columnKey) : undefined
        }
      />
    </div>
  )
}
