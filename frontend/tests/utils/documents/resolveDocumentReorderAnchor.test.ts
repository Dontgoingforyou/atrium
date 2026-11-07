import { describe, expect, it } from 'vitest'

import { resolveDocumentReorderAnchor } from '../../../src/utils/documents/resolveDocumentReorderAnchor'

describe('resolveDocumentReorderAnchor', () => {
  const ids = (ordered: string[], movedId: string) =>
    resolveDocumentReorderAnchor(
      ordered.map((id) => ({ id })),
      movedId,
    )

  it('для середины списка отдаёт before_id следующего', () => {
    expect(ids(['a', 'b', 'c'], 'b')).toEqual({ before_id: 'c' })
  })

  it('для последнего отдаёт after_id предыдущего', () => {
    expect(ids(['a', 'b', 'c'], 'c')).toEqual({ after_id: 'b' })
  })

  it('для первого при нескольких — before_id второго', () => {
    expect(ids(['a', 'b'], 'a')).toEqual({ before_id: 'b' })
  })

  it('для единственного элемента — null', () => {
    expect(ids(['only'], 'only')).toBeNull()
  })

  it('если id нет в списке — null', () => {
    expect(ids(['a', 'b'], 'missing')).toBeNull()
  })
})
