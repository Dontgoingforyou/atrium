import {
  DndContext,
  DragOverlay,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
  type DragOverEvent,
} from '@dnd-kit/core'
import { SortableContext, verticalListSortingStrategy } from '@dnd-kit/sortable'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useEffect, useMemo, useRef, useState } from 'react'

import { reorderPortalDocument, patchPortalDocumentWithCas } from '../../api/documents/documentsApi'
import { PORTAL_NAVIGATION_TREE_QUERY_KEY } from '../../api/queryKeys'
import { parentDocumentIdForNavSlug } from '@/domain/documents/documentNavSections'
import { userFacingMessageFromUnknown } from '../../utils/apiUserMessage'
import { documentChildrenQueryKey } from '../../utils/documents/documentNavigation'
import { resolveDocumentReorderAnchor } from '../../utils/documents/resolveDocumentReorderAnchor'
import { useNavTreeBranchCollapse } from '../../hooks/useNavTreeBranchCollapse'
import { useNotifyToast } from '../../hooks/useNotifyToast'
import type { NavDocBrief, PortalNavNodeTree } from '../../types/portalNavigation'
import {
  applyNestedDragMoveToIndex,
  applyTopLevelDragMove,
  findDocInTree,
  findNestedSiblingList,
  nestedSiblingIdSet,
  topLevelOrderKey,
  topLevelSlugByDocId,
  type CrossSectionLocal,
} from '@/utils/navigation/navCrossSectionTree'
import {
  nestedSiblingOrderKey,
  resolveNestedInsertIndex,
} from '@/utils/navigation/resolveNestedInsertIndex'
import { CrossSectionNavSection } from './CrossSectionNavSection'
import {
  NAV_DOC_DROP_ANIMATION,
  createCrossSectionCollisionDetection,
  docDndId,
  parseDocDndId,
} from './navDocumentDnd'
import styles from '@/styles/modules/layout/AppLayout.module.css'
import dndStyles from '@/styles/modules/layout/DraggablePortalNavTree.module.css'

type SectionLocal = CrossSectionLocal

type Props = {
  navTree: PortalNavNodeTree[]
  canEdit: boolean
  onCreate: (slug: string) => void
  createPending: boolean
}

type DragOrigin = {
  sections: SectionLocal[]
  movedId: string
  fromSlug: string | null
  fromParentId: string | null
}

function readNavDocRect(id: string): { top: number; height: number } | undefined {
  const safeId = id.replace(/\\/g, '\\\\').replace(/"/g, '\\"')
  const el = document.querySelector(`[data-nav-doc-id="${safeId}"]`)
  if (!(el instanceof HTMLElement)) return undefined
  const r = el.getBoundingClientRect()
  return { top: r.top, height: r.height }
}

function pointerYFromDrag(event: DragOverEvent | DragEndEvent): number | null {
  const translated = event.active.rect.current.translated
  if (translated) return translated.top + translated.height / 2
  const overRect = event.over?.rect
  if (overRect) return overRect.top + overRect.height / 2
  return null
}

/** DnD верхнего уровня между секциями «Документы» и «Документы для разработчиков». */
export function CrossSectionDraggableNav({ navTree, canEdit, onCreate, createPending }: Props) {
  const qc = useQueryClient()
  const notify = useNotifyToast()
  const { isCollapsed, toggle: toggleBranch } = useNavTreeBranchCollapse()
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 8 } }))

  const serverSections: SectionLocal[] = useMemo(
    () =>
      navTree.map((s) => ({
        id: s.id,
        slug: s.slug,
        title: s.title,
        docs: s.documents ?? [],
      })),
    [navTree],
  )

  const [sections, setSections] = useState(serverSections)
  const [prevServerSections, setPrevServerSections] = useState(serverSections)
  const [activeDocId, setActiveDocId] = useState<string | null>(null)
  const dragOriginRef = useRef<DragOrigin | null>(null)
  const sectionsRef = useRef(sections)

  useEffect(() => {
    sectionsRef.current = sections
  }, [sections])

  const persistMut = useMutation({
    mutationFn: async (payload: {
      documentId: string
      parent_document_id: string | null
      changeParent: boolean
      before_id?: string
      after_id?: string
      childrenParentId?: string | null
    }) => {
      if (payload.changeParent) {
        await patchPortalDocumentWithCas(payload.documentId, {
          parent_document_id: payload.parent_document_id,
        })
      }
      if (payload.before_id || payload.after_id) {
        await reorderPortalDocument(payload.documentId, {
          before_id: payload.before_id,
          after_id: payload.after_id,
        })
      }
      return payload
    },
    onSuccess: (payload) => {
      void qc.invalidateQueries({ queryKey: PORTAL_NAVIGATION_TREE_QUERY_KEY })
      const childrenParent =
        payload.childrenParentId ??
        (payload.changeParent ? payload.parent_document_id : null)
      if (childrenParent) {
        void qc.invalidateQueries({
          queryKey: documentChildrenQueryKey(childrenParent),
        })
      }
    },
    onError: (e) => {
      const fallback = dragOriginRef.current?.sections ?? serverSections
      sectionsRef.current = fallback
      setSections(fallback)
      notify(userFacingMessageFromUnknown(e))
    },
  })

  // Синхронизация с сервером вне активного drag/persist (без setState в effect).
  if (serverSections !== prevServerSections && !persistMut.isPending && !activeDocId) {
    setPrevServerSections(serverSections)
    setSections(serverSections)
  }

  const allTopIds = useMemo(
    () => sections.flatMap((s) => s.docs.map((d) => docDndId(d.id))),
    [sections],
  )

  const topLevelDocIdSet = useMemo(
    () => new Set(sections.flatMap((s) => s.docs.map((d) => d.id))),
    [sections],
  )

  const collisionDetection = useMemo(
    () =>
      createCrossSectionCollisionDetection(topLevelDocIdSet, (id) =>
        nestedSiblingIdSet(sections, id),
      ),
    [topLevelDocIdSet, sections],
  )

  const activeDoc = useMemo(() => {
    if (!activeDocId) return null
    for (const s of sections) {
      const found = findDocInTree(s.docs, activeDocId)
      if (found) return found
    }
    return null
  }, [activeDocId, sections])

  function moveNestedLive(movedId: string, pointerY: number) {
    const prev = sectionsRef.current
    let found: { parentId: string; list: NavDocBrief[] } | null = null
    for (const sec of prev) {
      found = findNestedSiblingList(sec.docs, movedId)
      if (found) break
    }
    if (!found) return

    const orderedIds = found.list.map((d) => d.id)
    const toIdx = resolveNestedInsertIndex(orderedIds, movedId, pointerY, readNavDocRect)
    if (toIdx === null) return
    const next = applyNestedDragMoveToIndex(prev, movedId, toIdx)
    if (!next) return

    let nextIds: string[] | null = null
    for (const sec of next) {
      const f = findNestedSiblingList(sec.docs, movedId)
      if (f) {
        nextIds = f.list.map((d) => d.id)
        break
      }
    }
    if (!nextIds) return
    if (nestedSiblingOrderKey(orderedIds) === nestedSiblingOrderKey(nextIds)) return

    sectionsRef.current = next
    setSections(next)
  }

  function moveItemsLive(overId: string | number, movedId: string) {
    const prev = sectionsRef.current
    const top = applyTopLevelDragMove(prev, movedId, overId)
    if (top && topLevelOrderKey(top) !== topLevelOrderKey(prev)) {
      sectionsRef.current = top
      setSections(top)
    }
  }

  function persistLayoutChange(origin: DragOrigin, current: SectionLocal[], movedId: string) {
    const slugById = topLevelSlugByDocId(current)
    const toSlug = slugById.get(movedId)
    if (toSlug) {
      const toSec = current.find((s) => s.slug === toSlug)
      if (!toSec) return
      const newIdx = toSec.docs.findIndex((d) => d.id === movedId)
      if (newIdx < 0) return

      const fromSlug = origin.fromSlug
      const changeParent = fromSlug != null && fromSlug !== toSlug
      const targetParent = parentDocumentIdForNavSlug(toSlug)
      const anchor = resolveDocumentReorderAnchor(toSec.docs, movedId)
      if (!anchor) return

      const originSec = fromSlug ? origin.sections.find((s) => s.slug === fromSlug) : null
      const originIdx = originSec?.docs.findIndex((d) => d.id === movedId) ?? -1
      const samePlace = !changeParent && originIdx === newIdx
      if (samePlace) return

      void persistMut.mutateAsync({
        documentId: movedId,
        parent_document_id: targetParent,
        changeParent,
        ...anchor,
        childrenParentId: targetParent,
      })
      return
    }

    for (const sec of current) {
      const found = findNestedSiblingList(sec.docs, movedId)
      if (!found) continue
      let originIdx = -1
      for (const s of origin.sections) {
        const originFound = findNestedSiblingList(s.docs, movedId)
        if (originFound) {
          originIdx = originFound.list.findIndex((d) => d.id === movedId)
          break
        }
      }
      const newIdx = found.list.findIndex((d) => d.id === movedId)
      if (newIdx < 0 || newIdx === originIdx) return
      const anchor = resolveDocumentReorderAnchor(found.list, movedId)
      if (!anchor) return
      void persistMut.mutateAsync({
        documentId: movedId,
        parent_document_id: null,
        changeParent: false,
        ...anchor,
        childrenParentId: found.parentId,
      })
      return
    }
  }

  function handleDragOver(event: DragOverEvent) {
    const { active, over } = event
    if (!over) return
    const movedId = parseDocDndId(active.id)
    if (!movedId) return
    const isNested = Boolean(nestedSiblingIdSet(sectionsRef.current, movedId))
    if (isNested) {
      const pointerY = pointerYFromDrag(event)
      if (pointerY == null) return
      moveNestedLive(movedId, pointerY)
      return
    }
    if (active.id === over.id) return
    moveItemsLive(over.id, movedId)
  }

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event
    const movedId = parseDocDndId(active.id)
    const origin = dragOriginRef.current
    dragOriginRef.current = null
    setActiveDocId(null)
    if (!movedId || !origin) {
      return
    }

    let finalSections = sectionsRef.current
    const isNested = Boolean(nestedSiblingIdSet(finalSections, movedId))
    if (isNested) {
      const pointerY = pointerYFromDrag(event)
      if (pointerY != null) {
        moveNestedLive(movedId, pointerY)
        finalSections = sectionsRef.current
      }
    } else if (over && active.id !== over.id) {
      const top = applyTopLevelDragMove(finalSections, movedId, over.id)
      if (top) {
        finalSections = top
        setSections(finalSections)
        sectionsRef.current = finalSections
      }
    }

    persistLayoutChange(origin, finalSections, movedId)
  }

  function handleDragCancel() {
    const origin = dragOriginRef.current
    dragOriginRef.current = null
    setActiveDocId(null)
    if (origin) {
      setSections(origin.sections)
      sectionsRef.current = origin.sections
    }
  }

  return (
    <div className={styles.navDocumentsScroll}>
      <div className={styles.navDocumentsInner}>
        <DndContext
          sensors={sensors}
          autoScroll
          collisionDetection={collisionDetection}
          onDragStart={({ active }) => {
            const id = parseDocDndId(active.id)
            if (!id) return
            setActiveDocId(id)
            const snapshot = sectionsRef.current
            const slugById = topLevelSlugByDocId(snapshot)
            let nestedParent: string | null = null
            for (const s of snapshot) {
              const found = findNestedSiblingList(s.docs, id)
              if (found) {
                nestedParent = found.parentId
                break
              }
            }
            const topSlug = slugById.get(id) ?? null
            dragOriginRef.current = {
              sections: snapshot,
              movedId: id,
              fromSlug: topSlug,
              fromParentId: nestedParent ?? (topSlug ? parentDocumentIdForNavSlug(topSlug) : null),
            }
          }}
          onDragOver={handleDragOver}
          onDragEnd={handleDragEnd}
          onDragCancel={handleDragCancel}
        >
          <SortableContext items={allTopIds} strategy={verticalListSortingStrategy}>
            {sections.map((section, sectionIndex) => (
              <CrossSectionNavSection
                key={section.id}
                section={section}
                sectionIndex={sectionIndex}
                canEdit={canEdit}
                createPending={createPending}
                onCreate={onCreate}
                isCollapsed={isCollapsed}
                onToggleBranch={toggleBranch}
                onNestedReorder={async (parentDocId, documentId, body) => {
                  await persistMut.mutateAsync({
                    documentId,
                    parent_document_id: null,
                    changeParent: false,
                    ...body,
                    childrenParentId: parentDocId,
                  })
                }}
              />
            ))}
          </SortableContext>
          <DragOverlay dropAnimation={NAV_DOC_DROP_ANIMATION}>
            {activeDoc ? (
              <div className={dndStyles.overlay}>
                <span>{activeDoc.title}</span>
              </div>
            ) : null}
          </DragOverlay>
        </DndContext>
      </div>
    </div>
  )
}
