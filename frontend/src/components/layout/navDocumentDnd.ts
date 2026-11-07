/** Общие константы и анимация DnD для деревьев документов в сайдбаре. */

import {
  closestCenter,
  defaultDropAnimationSideEffects,
  pointerWithin,
  rectIntersection,
  type CollisionDetection,
  type DropAnimation,
} from '@dnd-kit/core'
import {
  defaultAnimateLayoutChanges,
  type AnimateLayoutChanges,
} from '@dnd-kit/sortable'
import {
  parseDocDndId,
  parseSectionDndSlug,
} from '@/utils/navigation/navDocumentDndIds'

export {
  DOC_DND_PREFIX,
  SECTION_DND_PREFIX,
  docDndId,
  sectionDndId,
  parseDocDndId,
  parseSectionDndSlug,
} from '@/utils/navigation/navDocumentDndIds'

/** Плавный сдвиг соседей при сортировке и при вставке из другой секции. */
export const navDocAnimateLayoutChanges: AnimateLayoutChanges = (args) =>
  defaultAnimateLayoutChanges({ ...args, wasDragging: true })

export const NAV_DOC_LAYOUT_TRANSITION = 'transform 200ms cubic-bezier(0.25, 1, 0.5, 1)'

export const NAV_DOC_DROP_ANIMATION: DropAnimation = {
  duration: 200,
  easing: 'cubic-bezier(0.25, 1, 0.5, 1)',
  sideEffects: defaultDropAnimationSideEffects({
    styles: { active: { opacity: '0.4' } },
  }),
}

/**
 * Для перетаскивания верхнеуровневого документа между секциями:
 * игнорируем вложенные sortable (иначе closestCenter «липнет» к ним внизу списка)
 * и предпочитаем pointerWithin / пересечение с секцией.
 * Для nested — только collisions среди siblings того же родителя.
 */
export function createCrossSectionCollisionDetection(
  topLevelDocIds: ReadonlySet<string>,
  resolveNestedSiblingIds?: (activeDocId: string) => ReadonlySet<string> | null,
): CollisionDetection {
  return (args) => {
    const activeDocId = parseDocDndId(args.active.id)
    const draggingTopLevel = activeDocId != null && topLevelDocIds.has(activeDocId)
    const nestedSiblingIds =
      !draggingTopLevel && activeDocId && resolveNestedSiblingIds
        ? resolveNestedSiblingIds(activeDocId)
        : null

    const filterTargets = (collisions: ReturnType<CollisionDetection>) => {
      if (draggingTopLevel) {
        return collisions.filter((c) => {
          if (parseSectionDndSlug(c.id)) return true
          const id = parseDocDndId(c.id)
          return id != null && topLevelDocIds.has(id)
        })
      }
      if (nestedSiblingIds) {
        return collisions.filter((c) => {
          const id = parseDocDndId(c.id)
          return id != null && nestedSiblingIds.has(id)
        })
      }
      return collisions
    }

    const preferDocThenSection = (collisions: ReturnType<CollisionDetection>) => {
      if (collisions.length === 0) return collisions
      const docHit = collisions.find((c) => parseDocDndId(c.id))
      if (docHit) return [docHit]
      return [collisions[0]]
    }

    const pointerHits = filterTargets(pointerWithin(args))
    if (pointerHits.length > 0) return preferDocThenSection(pointerHits)

    const rectHits = filterTargets(rectIntersection(args))
    if (rectHits.length > 0) return preferDocThenSection(rectHits)

    const closest = filterTargets(closestCenter(args))
    return closest.length > 0 ? closest : closestCenter(args)
  }
}
