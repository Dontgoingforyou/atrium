import type { PortalTask } from '../../types/task'

export function resolveSubtaskReorderAnchor(
  ordered: PortalTask[],
  draggedId: string,
): { afterTaskId: string | null; beforeTaskId: string | null; status: string } | null {
  const dragged = ordered.find((t) => t.id === draggedId)
  if (!dragged) return null
  const idx = ordered.findIndex((t) => t.id === draggedId)
  if (idx < 0) return null
  if (idx === 0) {
    return {
      status: dragged.status,
      afterTaskId: null,
      beforeTaskId: ordered[1]?.id ?? null,
    }
  }
  return {
    status: dragged.status,
    afterTaskId: ordered[idx - 1]!.id,
    beforeTaskId: null,
  }
}
