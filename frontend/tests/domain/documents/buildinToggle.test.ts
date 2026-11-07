// @vitest-environment jsdom

import { describe, expect, it } from 'vitest'

import {
  applyBuildinToggleAutoOpen,
  BUILDIN_TOGGLE_BODY_ANIM_MS,
  BUILDIN_TOGGLE_BODY_EASE,
  buildinToggleBodyAnimMs,
  buildinToggleBodyHasContent,
  buildinToggleBodySlotState,
  buildinToggleExpandedDataset,
  buildinToggleInsertAttrs,
  buildinToggleOpenCommitDelayMs,
  shouldHoldToggleVisualOpen,
  shouldIgnoreBuildinToggleChromeMutation,
  shouldReleaseOpenToggleSlotHeight,
  shouldSettleToggleChromeOnNodeUpdate,
} from '@/domain/documents/buildinToggle'

describe('buildinToggleInsertAttrs', () => {
  it('новый блок сразу открыт — свернуть стрелкой', () => {
    expect(buildinToggleInsertAttrs()).toEqual({ title: 'Новый раздел', open: true })
  })

  it('слот тела: open/closed и data-expanded как у тулбара страницы', () => {
    expect(buildinToggleBodySlotState(true)).toBe('open')
    expect(buildinToggleBodySlotState(false)).toBe('closed')
    expect(buildinToggleExpandedDataset(true)).toBe('true')
    expect(buildinToggleExpandedDataset(false)).toBe('false')
    expect(BUILDIN_TOGGLE_BODY_ANIM_MS).toBe(250)
    expect(BUILDIN_TOGGLE_BODY_EASE).toBe('ease')
    expect(buildinToggleOpenCommitDelayMs()).toBe(buildinToggleBodyAnimMs())
    expect(shouldHoldToggleVisualOpen(false, true)).toBe(true)
    expect(shouldHoldToggleVisualOpen(false, false)).toBe(false)
    expect(shouldHoldToggleVisualOpen(null, true)).toBe(false)
  })

  it('мутации слота игнорит, правки тела — нет (иначе PM сносит анимацию)', () => {
    const body = document.createElement('div')
    const p = document.createElement('p')
    body.appendChild(p)
    const slot = document.createElement('div')
    expect(shouldIgnoreBuildinToggleChromeMutation(slot, body)).toBe(true)
    expect(shouldIgnoreBuildinToggleChromeMutation(body, body)).toBe(false)
    expect(shouldIgnoreBuildinToggleChromeMutation(p, body)).toBe(false)
    expect(shouldIgnoreBuildinToggleChromeMutation(null, body)).toBe(false)
  })
})

describe('shouldSettleToggleChromeOnNodeUpdate', () => {
  it('контент изменился, open тот же — settle запрещён (иначе Enter сбрасывает каретку)', () => {
    expect(
      shouldSettleToggleChromeOnNodeUpdate({
        pendingOpen: null,
        prevOpen: true,
        nextOpen: true,
      }),
    ).toBe(false)
    expect(
      shouldSettleToggleChromeOnNodeUpdate({
        pendingOpen: null,
        prevOpen: false,
        nextOpen: false,
      }),
    ).toBe(false)
  })

  it('open сменился без анимации — settle нужен', () => {
    expect(
      shouldSettleToggleChromeOnNodeUpdate({
        pendingOpen: null,
        prevOpen: true,
        nextOpen: false,
      }),
    ).toBe(true)
    expect(
      shouldSettleToggleChromeOnNodeUpdate({
        pendingOpen: null,
        prevOpen: false,
        nextOpen: true,
      }),
    ).toBe(true)
  })

  it('пока attrs.open отстаёт от pending — не откатывать слот', () => {
    expect(
      shouldSettleToggleChromeOnNodeUpdate({
        pendingOpen: false,
        prevOpen: true,
        nextOpen: true,
      }),
    ).toBe(false)
    expect(
      shouldSettleToggleChromeOnNodeUpdate({
        pendingOpen: true,
        prevOpen: false,
        nextOpen: false,
      }),
    ).toBe(false)
  })

  it('после анимации attrs догнал pending — settle к новому open', () => {
    expect(
      shouldSettleToggleChromeOnNodeUpdate({
        pendingOpen: false,
        prevOpen: true,
        nextOpen: false,
      }),
    ).toBe(true)
  })
})

describe('shouldReleaseOpenToggleSlotHeight', () => {
  it('снимает залипший height только у открытого слота вне анимации', () => {
    expect(
      shouldReleaseOpenToggleSlotHeight({
        isOpen: true,
        hasInlineHeight: true,
        isHoldingVisual: false,
      }),
    ).toBe(true)
    expect(
      shouldReleaseOpenToggleSlotHeight({
        isOpen: true,
        hasInlineHeight: true,
        isHoldingVisual: true,
      }),
    ).toBe(false)
    expect(
      shouldReleaseOpenToggleSlotHeight({
        isOpen: false,
        hasInlineHeight: true,
        isHoldingVisual: false,
      }),
    ).toBe(false)
    expect(
      shouldReleaseOpenToggleSlotHeight({
        isOpen: true,
        hasInlineHeight: false,
        isHoldingVisual: false,
      }),
    ).toBe(false)
  })
})

describe('buildinToggleBodyHasContent', () => {
  it('null → false', () => {
    expect(buildinToggleBodyHasContent(null)).toBe(false)
  })

  it('видимый текст → true', () => {
    const body = document.createElement('div')
    body.innerHTML = '<p>Текст</p>'
    expect(buildinToggleBodyHasContent(body)).toBe(true)
  })

  it('только img → true', () => {
    const body = document.createElement('div')
    body.innerHTML = '<img src="/x.png" />'
    expect(buildinToggleBodyHasContent(body)).toBe(true)
  })

  it('пустое тело → false', () => {
    const body = document.createElement('div')
    expect(buildinToggleBodyHasContent(body)).toBe(false)
  })
})

describe('applyBuildinToggleAutoOpen', () => {
  it('без buildin-toggle возвращает исходный html', () => {
    expect(applyBuildinToggleAutoOpen('<p>x</p>')).toBe('<p>x</p>')
  })

  it('ставит open на details с контентом', () => {
    const html =
      '<details class="buildin-toggle"><summary>t</summary><div class="buildin-toggle-body"><p>Hi</p></div></details>'
    const doc = new DOMParser().parseFromString(applyBuildinToggleAutoOpen(html), 'text/html')
    expect(doc.querySelector('details.buildin-toggle')?.hasAttribute('open')).toBe(true)
  })

  it('снимает open при пустом теле', () => {
    const html =
      '<details class="buildin-toggle" open><summary>t</summary><div class="buildin-toggle-body"></div></details>'
    const doc = new DOMParser().parseFromString(applyBuildinToggleAutoOpen(html), 'text/html')
    expect(doc.querySelector('details.buildin-toggle')?.hasAttribute('open')).toBe(false)
  })

  it('раскрывает toggle с только изображением в теле', () => {
    const html =
      '<details class="buildin-toggle"><summary>t</summary><div class="buildin-toggle-body"><img src="/a.png" alt=""/></div></details>'
    const doc = new DOMParser().parseFromString(applyBuildinToggleAutoOpen(html), 'text/html')
    expect(doc.querySelector('details.buildin-toggle')?.hasAttribute('open')).toBe(true)
  })

  it('два toggle: полный открыт, пустой без open', () => {
    const html =
      '<details class="buildin-toggle"><summary>a</summary><div class="buildin-toggle-body"><p>x</p></div></details>' +
      '<details class="buildin-toggle" open><summary>b</summary><div class="buildin-toggle-body"></div></details>'
    const doc = new DOMParser().parseFromString(applyBuildinToggleAutoOpen(html), 'text/html')
    const toggles = [...doc.querySelectorAll('details.buildin-toggle')]
    expect(toggles).toHaveLength(2)
    expect(toggles[0].hasAttribute('open')).toBe(true)
    expect(toggles[1].hasAttribute('open')).toBe(false)
  })
})
