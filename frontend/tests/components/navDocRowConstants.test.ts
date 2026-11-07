import { describe, expect, it } from 'vitest'

import {
  MAX_VISUAL_DEPTH,
  NAV_DOC_BASE_PADDING,
  NAV_DOC_DEPTH_PX,
  navDocIndentStyle,
  navDocNeedsCollapseSpace,
} from '../../src/components/layout/navDocRowConstants'

describe('navDocIndentStyle', () => {
  it('глубина 0 — без отступа (вровень с заголовком секции)', () => {
    expect(navDocIndentStyle(0)).toEqual({ paddingLeft: 0 })
  })

  it('отступ растёт на NAV_DOC_DEPTH_PX за каждую единицу глубины', () => {
    expect(navDocIndentStyle(1)).toEqual({
      paddingLeft: NAV_DOC_BASE_PADDING + NAV_DOC_DEPTH_PX,
    })
    expect(navDocIndentStyle(3)).toEqual({
      paddingLeft: NAV_DOC_BASE_PADDING + 3 * NAV_DOC_DEPTH_PX,
    })
  })

  it('глубина выше MAX_VISUAL_DEPTH ограничивается', () => {
    const capped = navDocIndentStyle(MAX_VISUAL_DEPTH + 5)
    const atMax = navDocIndentStyle(MAX_VISUAL_DEPTH)
    expect(capped).toEqual(atMax)
  })
})

describe('navDocNeedsCollapseSpace', () => {
  it('заглушка нужна на любой глубине, включая корень', () => {
    expect(navDocNeedsCollapseSpace(0)).toBe(true)
    expect(navDocNeedsCollapseSpace(1)).toBe(true)
    expect(navDocNeedsCollapseSpace(3)).toBe(true)
  })
})
