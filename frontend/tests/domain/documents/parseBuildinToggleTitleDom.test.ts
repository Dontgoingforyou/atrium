// @vitest-environment jsdom

import { describe, expect, it } from 'vitest'

import { parseBuildinToggleTitle } from '@/domain/documents/buildinToggleTitle'

function detailsFromHtml(html: string): Element {
  const wrap = document.createElement('div')
  wrap.innerHTML = html
  const details = wrap.querySelector('details')
  if (!details) throw new Error('нет details')
  return details
}

describe('parseBuildinToggleTitle DOM', () => {
  it('читает summary', () => {
    const el = detailsFromHtml(
      '<details class="buildin-toggle"><summary>ЧТО</summary><div class="buildin-toggle-body"><p></p></div></details>',
    )
    expect(parseBuildinToggleTitle(el)).toBe('ЧТО')
  })

  it('пустой summary + title на details', () => {
    const el = detailsFromHtml(
      '<details class="buildin-toggle" title="ЧТО"><summary></summary><div class="buildin-toggle-body"><p></p></div></details>',
    )
    expect(parseBuildinToggleTitle(el)).toBe('ЧТО')
  })

  it('игнорирует chrome NodeView в summary', () => {
    const el = detailsFromHtml(
      '<details class="buildin-toggle"><summary>' +
        '<span class="buildin-toggle-arrow">▶</span>' +
        '<input class="buildin-toggle-title-input" value="не из value">' +
        '<button type="button" class="buildin-toggle-delete">×</button>' +
        '</summary><div class="buildin-toggle-body"><p></p></div></details>',
    )
    el.setAttribute('title', 'ЧТО')
    expect(parseBuildinToggleTitle(el)).toBe('ЧТО')
  })
})
