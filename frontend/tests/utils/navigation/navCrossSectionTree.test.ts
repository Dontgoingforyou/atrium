import { describe, expect, it } from 'vitest'

import type { NavDocBrief } from '@/types/portalNavigation'
import {
  applyNestedDragMove,
  applyNestedDragMoveToIndex,
  applyTopLevelDragMove,
  findDocInTree,
  findNestedSiblingList,
  nestedSiblingIdSet,
  replaceChildren,
  sectionSlugForDoc,
  topLevelInsertId,
  topLevelOrderKey,
  type CrossSectionLocal,
} from '@/utils/navigation/navCrossSectionTree'
import { docDndId, sectionDndId } from '@/utils/navigation/navDocumentDndIds'

function doc(id: string, children: NavDocBrief[] = []): NavDocBrief {
  return { id, title: id, children }
}

function sectionsFixture(): CrossSectionLocal[] {
  return [
    {
      slug: 'a',
      title: 'A',
      id: 'sec-a',
      docs: [doc('a1', [doc('a1-1'), doc('a1-2')]), doc('a2')],
    },
    {
      slug: 'b',
      title: 'B',
      id: 'sec-b',
      docs: [doc('b1')],
    },
  ]
}

describe('findDocInTree / findNestedSiblingList / replaceChildren', () => {
  it('находит вложенный документ', () => {
    const tree = [doc('a1', [doc('a1-1')])]
    expect(findDocInTree(tree, 'a1-1')?.id).toBe('a1-1')
    expect(findDocInTree(tree, 'missing')).toBeNull()
  })

  it('находит список siblings у родителя', () => {
    const tree = [doc('a1', [doc('a1-1'), doc('a1-2')])]
    const found = findNestedSiblingList(tree, 'a1-2')
    expect(found?.parentId).toBe('a1')
    expect(found?.list.map((d) => d.id)).toEqual(['a1-1', 'a1-2'])
  })

  it('replaceChildren заменяет детей у родителя', () => {
    const tree = [doc('a1', [doc('a1-1'), doc('a1-2')])]
    const next = replaceChildren(tree, 'a1', [doc('a1-2'), doc('a1-1')])
    expect(next[0]!.children!.map((c) => c.id)).toEqual(['a1-2', 'a1-1'])
  })
})

describe('sectionSlugForDoc / topLevelInsertId / topLevelOrderKey', () => {
  it('sectionSlugForDoc для вложенного узла', () => {
    expect(sectionSlugForDoc(sectionsFixture(), 'a1-1')).toBe('a')
    expect(sectionSlugForDoc(sectionsFixture(), 'b1')).toBe('b')
    expect(sectionSlugForDoc(sectionsFixture(), 'x')).toBeNull()
  })

  it('topLevelInsertId: top-level и nested → корневой предок', () => {
    const docs = sectionsFixture()[0]!.docs
    expect(topLevelInsertId(docs, 'a2')).toBe('a2')
    expect(topLevelInsertId(docs, 'a1-1')).toBe('a1')
    expect(topLevelInsertId(docs, null)).toBeNull()
    expect(topLevelInsertId(docs, 'missing')).toBeNull()
  })

  it('topLevelOrderKey стабилен по slug и id', () => {
    expect(topLevelOrderKey(sectionsFixture())).toBe('a:a1,a2|b:b1')
  })
})

describe('applyTopLevelDragMove', () => {
  it('переставляет документы внутри секции', () => {
    const next = applyTopLevelDragMove(sectionsFixture(), 'a1', docDndId('a2'))
    expect(next?.find((s) => s.slug === 'a')?.docs.map((d) => d.id)).toEqual(['a2', 'a1'])
  })

  it('переносит документ в другую секцию (over section)', () => {
    const next = applyTopLevelDragMove(sectionsFixture(), 'a2', sectionDndId('b'))
    expect(next?.find((s) => s.slug === 'a')?.docs.map((d) => d.id)).toEqual(['a1'])
    expect(next?.find((s) => s.slug === 'b')?.docs.map((d) => d.id)).toEqual(['b1', 'a2'])
  })

  it('неизвестный movedId → null', () => {
    expect(applyTopLevelDragMove(sectionsFixture(), 'missing', docDndId('a2'))).toBeNull()
  })

  it('та же позиция → null', () => {
    expect(applyTopLevelDragMove(sectionsFixture(), 'a1', docDndId('a1'))).toBeNull()
  })
})

describe('applyNestedDragMove', () => {
  it('переставляет siblings под одним родителем', () => {
    const next = applyNestedDragMove(sectionsFixture(), 'a1-1', 'a1-2')
    const parent = next?.find((s) => s.slug === 'a')?.docs.find((d) => d.id === 'a1')
    expect(parent?.children?.map((c) => c.id)).toEqual(['a1-2', 'a1-1'])
  })

  it('over не из того же списка → null', () => {
    expect(applyNestedDragMove(sectionsFixture(), 'a1-1', 'a2')).toBeNull()
  })
})

describe('applyNestedDragMoveToIndex', () => {
  it('ставит nested на индекс', () => {
    const next = applyNestedDragMoveToIndex(sectionsFixture(), 'a1-1', 1)
    const parent = next?.find((s) => s.slug === 'a')?.docs.find((d) => d.id === 'a1')
    expect(parent?.children?.map((c) => c.id)).toEqual(['a1-2', 'a1-1'])
  })

  it('null при том же индексе', () => {
    expect(applyNestedDragMoveToIndex(sectionsFixture(), 'a1-1', 0)).toBeNull()
  })

  it('null за границами списка', () => {
    expect(applyNestedDragMoveToIndex(sectionsFixture(), 'a1-1', -1)).toBeNull()
    expect(applyNestedDragMoveToIndex(sectionsFixture(), 'a1-1', 2)).toBeNull()
  })
})

describe('nestedSiblingIdSet', () => {
  it('возвращает siblings nested', () => {
    const set = nestedSiblingIdSet(sectionsFixture(), 'a1-1')
    expect(set ? [...set].sort() : null).toEqual(['a1-1', 'a1-2'])
  })

  it('null для top-level', () => {
    expect(nestedSiblingIdSet(sectionsFixture(), 'a1')).toBeNull()
  })
})
