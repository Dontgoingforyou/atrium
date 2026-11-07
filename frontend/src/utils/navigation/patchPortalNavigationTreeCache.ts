import type { QueryClient } from '@tanstack/react-query'

import { PORTAL_NAVIGATION_TREE_QUERY_KEY } from '../../api/queryKeys'
import type { NavDocBrief, PortalNavNodeTree } from '../../types/portalNavigation'

/** Патч одного документа в дереве; вернуть тот же объект — no-op. */
type NavDocPatch = (d: NavDocBrief) => NavDocBrief

function patchDocField(
  docs: NavDocBrief[] | undefined,
  documentId: string,
  patch: NavDocPatch,
): NavDocBrief[] | undefined {
  if (!docs?.length) {
    return docs
  }
  let changed = false
  const next = docs.map((d) => {
    if (d.id === documentId) {
      const patched = patch(d)
      if (patched === d) {
        return d
      }
      changed = true
      return patched
    }
    const ch = patchDocField(d.children, documentId, patch)
    if (ch !== d.children) {
      changed = true
      return { ...d, children: ch }
    }
    return d
  })
  return changed ? next : docs
}

function patchNodesField(
  nodes: PortalNavNodeTree[],
  documentId: string,
  patch: NavDocPatch,
): PortalNavNodeTree[] {
  let changed = false
  const next = nodes.map((n) => {
    const docs = patchDocField(n.documents, documentId, patch)
    const children = patchNodesField(n.children, documentId, patch)
    if (docs !== n.documents || children !== n.children) {
      changed = true
      return { ...n, documents: docs, children }
    }
    return n
  })
  return changed ? next : nodes
}

function appendChildUnderDocs(
  docs: NavDocBrief[] | undefined,
  parentDocumentId: string,
  child: NavDocBrief,
): NavDocBrief[] | undefined {
  if (!docs?.length) {
    return docs
  }
  let changed = false
  const next = docs.map((d) => {
    if (d.id === parentDocumentId) {
      changed = true
      return { ...d, children: [child, ...(d.children ?? [])] }
    }
    const ch = appendChildUnderDocs(d.children, parentDocumentId, child)
    if (ch !== d.children) {
      changed = true
      return { ...d, children: ch }
    }
    return d
  })
  return changed ? next : docs
}

function appendChildInNodes(
  nodes: PortalNavNodeTree[],
  parentDocumentId: string,
  child: NavDocBrief,
): PortalNavNodeTree[] {
  let changed = false
  const next = nodes.map((n) => {
    const docs = appendChildUnderDocs(n.documents, parentDocumentId, child)
    const children = appendChildInNodes(n.children, parentDocumentId, child)
    if (docs !== n.documents || children !== n.children) {
      changed = true
      return { ...n, documents: docs, children }
    }
    return n
  })
  return changed ? next : nodes
}

function removeDocFromDocs(
  docs: NavDocBrief[] | undefined,
  documentId: string,
): NavDocBrief[] | undefined {
  if (!docs?.length) {
    return docs
  }
  let changed = false
  const filtered = docs.filter((d) => {
    if (d.id === documentId) {
      changed = true
      return false
    }
    return true
  })
  const next = filtered.map((d) => {
    const ch = removeDocFromDocs(d.children, documentId)
    let shortcuts = d.shortcuts
    if (shortcuts?.length) {
      const nextShortcuts = shortcuts.filter((s) => s.id !== documentId)
      if (nextShortcuts.length !== shortcuts.length) {
        changed = true
        shortcuts = nextShortcuts.length > 0 ? nextShortcuts : undefined
      }
    }
    if (ch !== d.children || shortcuts !== d.shortcuts) {
      changed = true
      return { ...d, children: ch, shortcuts }
    }
    return d
  })
  return changed ? next : docs
}


export function filterNavTreeHiddenDocuments(
  nodes: PortalNavNodeTree[],
  hiddenIds: ReadonlySet<string>,
): PortalNavNodeTree[] {
  if (hiddenIds.size === 0) {
    return nodes
  }
  return nodes.map((n) => ({
    ...n,
    documents: filterHiddenDocs(n.documents, hiddenIds),
    children: filterNavTreeHiddenDocuments(n.children, hiddenIds),
  }))
}

function filterHiddenDocs(
  docs: NavDocBrief[] | undefined,
  hiddenIds: ReadonlySet<string>,
): NavDocBrief[] | undefined {
  if (!docs?.length) {
    return docs
  }
  const next = docs
    .filter((d) => !hiddenIds.has(d.id))
    .map((d) => {
      const children = filterHiddenDocs(d.children, hiddenIds)
      const shortcuts = d.shortcuts?.filter((s) => !hiddenIds.has(s.id))
      return {
        ...d,
        children,
        shortcuts: shortcuts?.length ? shortcuts : undefined,
      }
    })
  return next
}

function removeDocFromNodes(nodes: PortalNavNodeTree[], documentId: string): PortalNavNodeTree[] {
  let changed = false
  const next = nodes.map((n) => {
    const docs = removeDocFromDocs(n.documents, documentId)
    const children = removeDocFromNodes(n.children, documentId)
    if (docs !== n.documents || children !== n.children) {
      changed = true
      return { ...n, documents: docs, children }
    }
    return n
  })
  return changed ? next : nodes
}

/** Убрать документ (и поддерево в nav-кэше) оптимистично при удалении. */
export function patchNavigationTreeRemoveDocument(qc: QueryClient, documentId: string): void {
  qc.setQueryData<PortalNavNodeTree[]>(PORTAL_NAVIGATION_TREE_QUERY_KEY, (old) => {
    if (!old?.length) {
      return old
    }
    const next = removeDocFromNodes(old, documentId)
    return next === old ? old : next
  })
}

/** Сразу обновить заголовок документа в кэше дерева навигации (сайдбар). */
export function patchNavigationTreeDocumentTitle(qc: QueryClient, documentId: string, title: string): void {
  qc.setQueryData<PortalNavNodeTree[]>(PORTAL_NAVIGATION_TREE_QUERY_KEY, (old) => {
    if (!old?.length) {
      return old
    }
    const next = patchNodesField(old, documentId, (d) =>
      d.title === title ? d : { ...d, title },
    )
    return next === old ? old : next
  })
}

/** Сразу обновить эмодзи-иконку документа в кэше дерева навигации (сайдбар). */
export function patchNavigationTreeDocumentIcon(
  qc: QueryClient,
  documentId: string,
  iconEmoji: string | null,
): void {
  qc.setQueryData<PortalNavNodeTree[]>(PORTAL_NAVIGATION_TREE_QUERY_KEY, (old) => {
    if (!old?.length) {
      return old
    }
    const next = patchNodesField(old, documentId, (d) =>
      (d.icon_emoji ?? null) === iconEmoji ? d : { ...d, icon_emoji: iconEmoji },
    )
    return next === old ? old : next
  })
}

/** Добавить дочерний документ под родителем в кэше дерева (до refetch с сервера). */
export function patchNavigationTreeAppendChildDocument(
  qc: QueryClient,
  parentDocumentId: string,
  child: NavDocBrief,
): void {
  qc.setQueryData<PortalNavNodeTree[]>(PORTAL_NAVIGATION_TREE_QUERY_KEY, (old) => {
    if (!old?.length) {
      return old
    }
    const next = appendChildInNodes(old, parentDocumentId, child)
    return next === old ? old : next
  })
}

/** Принудительно подтянуть дерево с сервера (счётчики и прочее). */
export function refetchPortalNavigationTree(qc: QueryClient): void {
  void qc.refetchQueries({ queryKey: [...PORTAL_NAVIGATION_TREE_QUERY_KEY] })
}

function patchDocsSiblingOrder(
  docs: NavDocBrief[] | undefined,
  siblingRef: NavDocBrief[],
  newSiblings: NavDocBrief[],
): NavDocBrief[] | undefined {
  if (!docs) {
    return docs
  }
  if (docs === siblingRef) {
    return newSiblings
  }
  let changed = false
  const next = docs.map((d) => {
    const ch = patchDocsSiblingOrder(d.children, siblingRef, newSiblings)
    if (ch !== d.children) {
      changed = true
      return { ...d, children: ch }
    }
    return d
  })
  return changed ? next : docs
}

function patchNavDocReorderInNodes(
  nodes: PortalNavNodeTree[],
  siblingRef: NavDocBrief[],
  newSiblings: NavDocBrief[],
): PortalNavNodeTree[] {
  return nodes.map((n) => {
    const documents = patchDocsSiblingOrder(n.documents, siblingRef, newSiblings)
    const children = patchNavDocReorderInNodes(n.children, siblingRef, newSiblings)
    if (documents !== n.documents || children !== n.children) {
      return { ...n, documents, children }
    }
    return n
  })
}

/** Оптимистично переставить сиблингов-документов в кэше (та же ссылка на массив, что в дереве). */
export function patchNavigationTreeReorderSiblingDocs(
  qc: QueryClient,
  siblingRef: NavDocBrief[],
  newSiblings: NavDocBrief[],
): void {
  qc.setQueryData<PortalNavNodeTree[]>(PORTAL_NAVIGATION_TREE_QUERY_KEY, (old) => {
    if (!old?.length) {
      return old
    }
    return patchNavDocReorderInNodes(old, siblingRef, newSiblings)
  })
}

function reorderChildrenUnderDocs(
  docs: NavDocBrief[] | undefined,
  parentDocumentId: string,
  orderedChildIds: readonly string[],
): NavDocBrief[] | undefined {
  if (!docs?.length) {
    return docs
  }
  let changed = false
  const next = docs.map((d) => {
    if (d.id === parentDocumentId) {
      const children = d.children ?? []
      if (children.length === 0) {
        return d
      }
      const byId = new Map(children.map((c) => [c.id, c]))
      const reordered: NavDocBrief[] = []
      for (const id of orderedChildIds) {
        const row = byId.get(id)
        if (row) {
          reordered.push(row)
          byId.delete(id)
        }
      }
      for (const leftover of byId.values()) {
        reordered.push(leftover)
      }
      const same =
        reordered.length === children.length && reordered.every((c, i) => c.id === children[i]?.id)
      if (same) {
        return d
      }
      changed = true
      return { ...d, children: reordered }
    }
    const ch = reorderChildrenUnderDocs(d.children, parentDocumentId, orderedChildIds)
    if (ch !== d.children) {
      changed = true
      return { ...d, children: ch }
    }
    return d
  })
  return changed ? next : docs
}

function reorderChildrenInNodes(
  nodes: PortalNavNodeTree[],
  parentDocumentId: string,
  orderedChildIds: readonly string[],
): PortalNavNodeTree[] {
  return nodes.map((n) => {
    const documents = reorderChildrenUnderDocs(n.documents, parentDocumentId, orderedChildIds)
    const children = reorderChildrenInNodes(n.children, parentDocumentId, orderedChildIds)
    if (documents !== n.documents || children !== n.children) {
      return { ...n, documents, children }
    }
    return n
  })
}

export function patchNavigationTreeReorderChildrenOfParent(
  qc: QueryClient,
  parentDocumentId: string,
  orderedChildIds: readonly string[],
): void {
  qc.setQueryData<PortalNavNodeTree[]>(PORTAL_NAVIGATION_TREE_QUERY_KEY, (old) => {
    if (!old?.length) {
      return old
    }
    return reorderChildrenInNodes(old, parentDocumentId, orderedChildIds)
  })
}

function patchNavNodesSiblingOrder(
  nodes: PortalNavNodeTree[],
  siblingRef: PortalNavNodeTree[],
  newSiblings: PortalNavNodeTree[],
): PortalNavNodeTree[] {
  if (nodes === siblingRef) {
    return newSiblings
  }
  return nodes.map((n) => {
    const children = patchNavNodesSiblingOrder(n.children, siblingRef, newSiblings)
    if (children !== n.children) {
      return { ...n, children }
    }
    return n
  })
}

/** Оптимистично переставить узлы навигации среди сиблингов */
export function patchNavigationTreeReorderSiblingNavNodes(
  qc: QueryClient,
  siblingRef: PortalNavNodeTree[],
  newSiblings: PortalNavNodeTree[],
): void {
  qc.setQueryData<PortalNavNodeTree[]>(PORTAL_NAVIGATION_TREE_QUERY_KEY, (old) => {
    if (!old?.length) {
      return old
    }
    return patchNavNodesSiblingOrder(old, siblingRef, newSiblings)
  })
}
