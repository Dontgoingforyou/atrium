import { QueryClient } from '@tanstack/react-query'
import { describe, expect, it } from 'vitest'

import { PORTAL_NAVIGATION_TREE_QUERY_KEY } from '@/api/queryKeys'
import type { PortalNavNodeTree } from '@/types/portalNavigation'
import {
  filterNavTreeHiddenDocuments,
  patchNavigationTreeAppendChildDocument,
  patchNavigationTreeDocumentIcon,
  patchNavigationTreeDocumentTitle,
  patchNavigationTreeRemoveDocument,
  patchNavigationTreeReorderChildrenOfParent,
  patchNavigationTreeReorderSiblingDocs,
  patchNavigationTreeReorderSiblingNavNodes,
} from '@/utils/navigation/patchPortalNavigationTreeCache'

const sampleTree: PortalNavNodeTree[] = [
  {
    id: 'nav-1',
    slug: 's',
    title: 'Раздел',
    sort_order: 10,
    document_count_subtree: 2,
    documents: [
      {
        id: 'doc-root',
        title: 'Старое',
        children: [{ id: 'doc-child', title: 'Ребёнок', children: [] }],
      },
    ],
    children: [],
  },
]

describe('patchPortalNavigationTreeCache', () => {
  it('обновляет заголовок документа в дереве', () => {
    const qc = new QueryClient()
    qc.setQueryData(PORTAL_NAVIGATION_TREE_QUERY_KEY, sampleTree)
    patchNavigationTreeDocumentTitle(qc, 'doc-root', 'Новое')
    const next = qc.getQueryData<PortalNavNodeTree[]>(PORTAL_NAVIGATION_TREE_QUERY_KEY)
    expect(next?.[0]?.documents?.[0]?.title).toBe('Новое')
    expect(next?.[0]?.documents?.[0]?.children?.[0]?.title).toBe('Ребёнок')
  })

  it('тот же заголовок не меняет дерево', () => {
    const qc = new QueryClient()
    qc.setQueryData(PORTAL_NAVIGATION_TREE_QUERY_KEY, sampleTree)
    patchNavigationTreeDocumentTitle(qc, 'doc-root', 'Старое')
    expect(qc.getQueryData<PortalNavNodeTree[]>(PORTAL_NAVIGATION_TREE_QUERY_KEY)).toBe(sampleTree)
  })

  it('обновляет эмодзи документа в дереве', () => {
    const qc = new QueryClient()
    qc.setQueryData(PORTAL_NAVIGATION_TREE_QUERY_KEY, structuredClone(sampleTree))
    patchNavigationTreeDocumentIcon(qc, 'doc-root', '📎')
    const next = qc.getQueryData<PortalNavNodeTree[]>(PORTAL_NAVIGATION_TREE_QUERY_KEY)
    expect(next?.[0]?.documents?.[0]?.icon_emoji).toBe('📎')
  })

  it('добавляет дочерний документ под родителем', () => {
    const qc = new QueryClient()
    qc.setQueryData(PORTAL_NAVIGATION_TREE_QUERY_KEY, structuredClone(sampleTree))
    patchNavigationTreeAppendChildDocument(qc, 'doc-root', { id: 'new-id', title: 'Без названия', children: [] })
    const next = qc.getQueryData<PortalNavNodeTree[]>(PORTAL_NAVIGATION_TREE_QUERY_KEY)
    const kids = next?.[0]?.documents?.[0]?.children ?? []
    expect(kids.some((c) => c.id === 'new-id')).toBe(true)
  })

  it('append при неизвестном parent не меняет кэш', () => {
    const qc = new QueryClient()
    const tree = structuredClone(sampleTree)
    qc.setQueryData(PORTAL_NAVIGATION_TREE_QUERY_KEY, tree)
    patchNavigationTreeAppendChildDocument(qc, 'missing-parent', {
      id: 'new-id',
      title: 'Без названия',
      children: [],
    })
    expect(qc.getQueryData<PortalNavNodeTree[]>(PORTAL_NAVIGATION_TREE_QUERY_KEY)).toBe(tree)
  })

  it('переставляет детей под родителем по списку id', () => {
    const qc = new QueryClient()
    const tree = structuredClone(sampleTree)
    tree[0]!.documents = [
      {
        id: 'doc-root',
        title: 'Корень',
        children: [
          { id: 'c1', title: 'Один', children: [] },
          { id: 'c2', title: 'Два', children: [] },
          { id: 'c3', title: 'Три', children: [] },
        ],
      },
    ]
    qc.setQueryData(PORTAL_NAVIGATION_TREE_QUERY_KEY, tree)
    patchNavigationTreeReorderChildrenOfParent(qc, 'doc-root', ['c3', 'c1', 'c2'])
    const next = qc.getQueryData<PortalNavNodeTree[]>(PORTAL_NAVIGATION_TREE_QUERY_KEY)
    expect(next?.[0]?.documents?.[0]?.children?.map((c) => c.id)).toEqual(['c3', 'c1', 'c2'])
  })

  it('переставляет корневые документы раздела по ссылке на массив сиблингов', () => {
    const qc = new QueryClient()
    const tree = structuredClone(sampleTree)
    tree[0].documents = [
      { id: 'd1', title: 'Первый', children: [] },
      { id: 'd2', title: 'Второй', children: [] },
    ]
    const siblings = tree[0].documents!
    qc.setQueryData(PORTAL_NAVIGATION_TREE_QUERY_KEY, tree)
    const reordered = [siblings[1], siblings[0]]
    patchNavigationTreeReorderSiblingDocs(qc, siblings, reordered)
    const next = qc.getQueryData<PortalNavNodeTree[]>(PORTAL_NAVIGATION_TREE_QUERY_KEY)
    expect(next?.[0]?.documents?.map((d) => d.id)).toEqual(['d2', 'd1'])
  })

  it('переставляет узлы навигации верхнего уровня', () => {
    const qc = new QueryClient()
    const tree: PortalNavNodeTree[] = [
      {
        id: 'a',
        slug: 'a',
        title: 'A',
        sort_order: 10,
        document_count_subtree: 0,
        documents: [],
        children: [],
      },
      {
        id: 'b',
        slug: 'b',
        title: 'B',
        sort_order: 20,
        document_count_subtree: 0,
        documents: [],
        children: [],
      },
    ]
    qc.setQueryData(PORTAL_NAVIGATION_TREE_QUERY_KEY, tree)
    const top = qc.getQueryData<PortalNavNodeTree[]>(PORTAL_NAVIGATION_TREE_QUERY_KEY)!
    patchNavigationTreeReorderSiblingNavNodes(qc, top, [top[1], top[0]])
    const next = qc.getQueryData<PortalNavNodeTree[]>(PORTAL_NAVIGATION_TREE_QUERY_KEY)
    expect(next?.map((n) => n.id)).toEqual(['b', 'a'])
  })

  it('удаляет документ и ярлыки на него из nav-кэша', () => {
    const qc = new QueryClient()
    const tree: PortalNavNodeTree[] = [
      {
        id: 'nav-1',
        slug: 's',
        title: 'Раздел',
        sort_order: 10,
        document_count_subtree: 2,
        documents: [
          {
            id: 'doc-source',
            title: 'Источник',
            children: [],
            shortcuts: [{ id: 'doc-target', title: 'Ярлык на target', children: [] }],
          },
          {
            id: 'doc-target',
            title: 'Target',
            children: [],
          },
        ],
        children: [],
      },
    ]
    qc.setQueryData(PORTAL_NAVIGATION_TREE_QUERY_KEY, tree)
    patchNavigationTreeRemoveDocument(qc, 'doc-target')
    const next = qc.getQueryData<PortalNavNodeTree[]>(PORTAL_NAVIGATION_TREE_QUERY_KEY)
    const docs = next?.[0]?.documents ?? []
    expect(docs.map((d) => d.id)).toEqual(['doc-source'])
    expect(docs[0]?.shortcuts).toBeUndefined()
  })

  it('удаляет вложенный документ из children', () => {
    const qc = new QueryClient()
    qc.setQueryData(PORTAL_NAVIGATION_TREE_QUERY_KEY, structuredClone(sampleTree))
    patchNavigationTreeRemoveDocument(qc, 'doc-child')
    const next = qc.getQueryData<PortalNavNodeTree[]>(PORTAL_NAVIGATION_TREE_QUERY_KEY)
    expect(next?.[0]?.documents?.[0]?.id).toBe('doc-root')
    expect(next?.[0]?.documents?.[0]?.children ?? []).toEqual([])
  })
})

describe('filterNavTreeHiddenDocuments', () => {
  it('скрывает документы и ярлыки по pending-delete id', () => {
    const tree: PortalNavNodeTree[] = [
      {
        id: 'nav-1',
        slug: 's',
        title: 'Раздел',
        sort_order: 10,
        document_count_subtree: 2,
        documents: [
          {
            id: 'keep',
            title: 'Остаётся',
            children: [{ id: 'hidden-child', title: 'Скрытый ребёнок', children: [] }],
            shortcuts: [{ id: 'hidden-root', title: 'Ярлык', children: [] }],
          },
          { id: 'hidden-root', title: 'Скрытый корень', children: [] },
        ],
        children: [],
      },
    ]
    const filtered = filterNavTreeHiddenDocuments(tree, new Set(['hidden-root', 'hidden-child']))
    const docs = filtered[0]?.documents ?? []
    expect(docs.map((d) => d.id)).toEqual(['keep'])
    expect(docs[0]?.children ?? []).toEqual([])
    expect(docs[0]?.shortcuts).toBeUndefined()
  })

  it('возвращает то же дерево при пустом наборе hidden', () => {
    const filtered = filterNavTreeHiddenDocuments(sampleTree, new Set())
    expect(filtered).toBe(sampleTree)
  })
})
