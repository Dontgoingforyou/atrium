import { KANBAN_OTHER_BUCKET } from './kanbanDisplayCommon'

/** Минимальный hit collision detection — без зависимости domain от @dnd-kit. */
export type KanbanCollisionHit = { id: string | number }

export type ResolveKanbanBoardCollisionsInput<T extends KanbanCollisionHit> = {
  activeType: string | undefined
  activeId: string
  pointerHits: readonly T[]
  closestHits: readonly T[]
  columnIds: ReadonlySet<string>
  taskIdsInColumn: (status: string) => ReadonlySet<string>
}

function isColumnDropTarget(id: string, columnIds: ReadonlySet<string>): boolean {
  return columnIds.has(id) && id !== KANBAN_OTHER_BUCKET
}

export function resolveKanbanBoardCollisions<T extends KanbanCollisionHit>(
  input: ResolveKanbanBoardCollisionsInput<T>,
): T[] {
  const { activeType, activeId, pointerHits, closestHits, columnIds, taskIdsInColumn } = input

  if (activeType === 'column') {
    const isTarget = (id: string) => isColumnDropTarget(id, columnIds) && id !== activeId
    const pointerColumns = pointerHits.filter((hit) => isTarget(String(hit.id)))
    if (pointerColumns.length > 0) return [...pointerColumns]
    return closestHits.filter((hit) => isTarget(String(hit.id)))
  }

  const exactTaskHits = pointerHits.filter(
    ({ id }) => !columnIds.has(String(id)) && String(id) !== activeId,
  )
  if (exactTaskHits.length > 0) return [...exactTaskHits]

  const currentColHit = pointerHits.find(({ id }) => columnIds.has(String(id)))
  if (currentColHit) {
    const idsInCol = taskIdsInColumn(String(currentColHit.id))
    const nearestInCol = closestHits.filter(
      ({ id }) => idsInCol.has(String(id)) && String(id) !== activeId,
    )
    if (nearestInCol.length > 0) return [...nearestInCol]
    return [currentColHit]
  }

  return [...closestHits]
}
