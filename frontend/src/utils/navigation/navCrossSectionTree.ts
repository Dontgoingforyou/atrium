import { arrayMove } from '@dnd-kit/sortable'

import type { NavDocBrief } from '../../types/portalNavigation'
import { parseDocDndId, parseSectionDndSlug } from './navDocumentDndIds'

export type CrossSectionLocal = {
  slug: string
  title: string
  id: string
  docs: NavDocBrief[]
}

export function findDocInTree(docs: NavDocBrief[], id: string): NavDocBrief | null {
  for (const d of docs) {
    if (d.id === id) return d
    const nested = findDocInTree(d.children ?? [], id)
    if (nested) return nested
  }
  return null
}

export function findNestedSiblingList(
  docs: NavDocBrief[],
  docId: string,
): { parentId: string; list: NavDocBrief[] } | null {
  for (const d of docs) {
    const children = d.children ?? []
    if (children.some((c) => c.id === docId)) {
      return { parentId: d.id, list: children }
    }
    const nested = findNestedSiblingList(children, docId)
    if (nested) return nested
  }
  return null
}

export function replaceChildren(
  docs: NavDocBrief[],
  parentId: string,
  newChildren: NavDocBrief[],
): NavDocBrief[] {
  return docs.map((d) => {
    if (d.id === parentId) return { ...d, children: newChildren }
    if (d.children?.length) {
      return { ...d, children: replaceChildren(d.children, parentId, newChildren) }
    }
    return d
  })
}

/** Секция, в чьём дереве лежит документ (включая вложенных). */
export function sectionSlugForDoc(sections: CrossSectionLocal[], docId: string): string | null {
  for (const s of sections) {
    if (findDocInTree(s.docs, docId)) return s.slug
  }
  return null
}

/**
 * Id верхнеуровневого документа секции для позиции вставки.
 * Если over — вложенный узел, берём его корневого предка в секции.
 */
export function topLevelInsertId(
  sectionDocs: NavDocBrief[],
  overDocId: string | null,
): string | null {
  if (!overDocId) return null
  if (sectionDocs.some((d) => d.id === overDocId)) return overDocId
  for (const d of sectionDocs) {
    if (findDocInTree(d.children ?? [], overDocId)) return d.id
  }
  return null
}

export function topLevelSlugByDocId(sections: CrossSectionLocal[]): Map<string, string> {
  const m = new Map<string, string>()
  for (const s of sections) {
    for (const d of s.docs) m.set(d.id, s.slug)
  }
  return m
}

export function topLevelOrderKey(sections: CrossSectionLocal[]): string {
  return sections.map((s) => `${s.slug}:${s.docs.map((d) => d.id).join(',')}`).join('|')
}

/** Живой перенос/перестановка верхнеуровневого документа (без API). */
export function applyTopLevelDragMove(
  sections: CrossSectionLocal[],
  movedId: string,
  overId: string | number,
): CrossSectionLocal[] | null {
  const slugById = topLevelSlugByDocId(sections)
  const fromSlug = slugById.get(movedId)
  if (!fromSlug) return null

  const overDocId = parseDocDndId(overId)
  const toSlug =
    parseSectionDndSlug(overId) ??
    (overDocId ? (slugById.get(overDocId) ?? sectionSlugForDoc(sections, overDocId)) : null)
  if (!toSlug) return null

  const fromSec = sections.find((s) => s.slug === fromSlug)
  const toSec = sections.find((s) => s.slug === toSlug)
  if (!fromSec || !toSec) return null

  const fromIdx = fromSec.docs.findIndex((d) => d.id === movedId)
  if (fromIdx < 0) return null

  const insertAnchorId = topLevelInsertId(toSec.docs, overDocId)
  let newToDocs: NavDocBrief[]
  let newFromDocs: NavDocBrief[] | null = null

  if (fromSlug === toSlug) {
    const overIdx = insertAnchorId
      ? fromSec.docs.findIndex((d) => d.id === insertAnchorId)
      : fromSec.docs.length - 1
    if (overIdx < 0 || fromIdx === overIdx) return null
    newToDocs = arrayMove(fromSec.docs, fromIdx, overIdx)
  } else {
    const movedDoc = fromSec.docs[fromIdx]
    newFromDocs = fromSec.docs.filter((d) => d.id !== movedId)
    newToDocs = [...toSec.docs]
    const insertAt = insertAnchorId
      ? newToDocs.findIndex((d) => d.id === insertAnchorId)
      : newToDocs.length
    newToDocs.splice(insertAt < 0 ? newToDocs.length : insertAt, 0, movedDoc)
  }

  return sections.map((s) => {
    if (newFromDocs && s.slug === fromSlug) return { ...s, docs: newFromDocs }
    if (s.slug === toSlug) return { ...s, docs: newToDocs }
    return s
  })
}

export function applyNestedDragMove(
  sections: CrossSectionLocal[],
  movedId: string,
  overDocId: string,
): CrossSectionLocal[] | null {
  for (const sec of sections) {
    const found = findNestedSiblingList(sec.docs, movedId)
    if (!found) continue
    if (!found.list.some((c) => c.id === overDocId)) return null

    const fromIdx = found.list.findIndex((d) => d.id === movedId)
    const overIdx = found.list.findIndex((d) => d.id === overDocId)
    if (fromIdx < 0 || overIdx < 0 || fromIdx === overIdx) return null

    const newList = arrayMove(found.list, fromIdx, overIdx)
    return sections.map((s) =>
      s.slug === sec.slug ? { ...s, docs: replaceChildren(s.docs, found.parentId, newList) } : s,
    )
  }
  return null
}

export function applyNestedDragMoveToIndex(
  sections: CrossSectionLocal[],
  movedId: string,
  toIdx: number,
): CrossSectionLocal[] | null {
  for (const sec of sections) {
    const found = findNestedSiblingList(sec.docs, movedId)
    if (!found) continue
    const fromIdx = found.list.findIndex((d) => d.id === movedId)
    if (fromIdx < 0 || toIdx < 0 || toIdx >= found.list.length || fromIdx === toIdx) {
      return null
    }
    const newList = arrayMove(found.list, fromIdx, toIdx)
    return sections.map((s) =>
      s.slug === sec.slug ? { ...s, docs: replaceChildren(s.docs, found.parentId, newList) } : s,
    )
  }
  return null
}

export function nestedSiblingIdSet(
  sections: CrossSectionLocal[],
  movedId: string,
): Set<string> | null {
  for (const sec of sections) {
    const found = findNestedSiblingList(sec.docs, movedId)
    if (found) return new Set(found.list.map((d) => d.id))
  }
  return null
}
