import type { CSSProperties } from 'react'

import { navDocHasBranch } from '@/domain/documents/documentNavSections'
import type { NavDocBrief } from '../../types/portalNavigation'

/** Максимальная визуальная глубина отступа; логическая глубина в данных не ограничена. */
export const MAX_VISUAL_DEPTH = 7
export const NAV_DOC_BASE_PADDING = 8
export const NAV_DOC_DEPTH_PX = 14

export function navDocIndentStyle(depth: number): CSSProperties {
  const visualDepth = Math.min(depth, MAX_VISUAL_DEPTH)
  if (visualDepth === 0) {
    return { paddingLeft: 0 }
  }
  return {
    paddingLeft: NAV_DOC_BASE_PADDING + visualDepth * NAV_DOC_DEPTH_PX,
  }
}

export function navDocNeedsCollapseSpace(depth: number): boolean {
  return depth >= 0
}

/** Признак, скрыта ли ветка документа (есть ветка и она свёрнута). */
export function navDocBranchHidden(
  doc: NavDocBrief,
  isBranchCollapsed: (id: string) => boolean,
): boolean {
  return navDocHasBranch(doc) && isBranchCollapsed(doc.id)
}
