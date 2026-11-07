// @vitest-environment jsdom

import { describe, expect, it } from 'vitest'

import {
  rememberEmittedRichHtml,
  shouldApplyExternalRichHtml,
} from '@/utils/html/emittedRichHtml'

describe('shouldApplyExternalRichHtml', () => {
  it('не применяет, если sanitize(getHTML) совпадает с incoming', () => {
    const emitted = new Set<string>()
    const html = '<p>Список</p>'
    expect(shouldApplyExternalRichHtml(emitted, html, html)).toBe(false)
  })

  it('не применяет свой же onUpdate после sanitize', () => {
    const emitted = new Set<string>()
    const raw = '<p><a href="https://example.com">x</a></p>'
    rememberEmittedRichHtml(emitted, raw)
    expect(shouldApplyExternalRichHtml(emitted, '<p>другое</p>', raw)).toBe(false)
  })

  it('не применяет echo своего H1 после onUpdate', () => {
    const emitted = new Set<string>()
    const raw = '<h1>Hello</h1>'
    rememberEmittedRichHtml(emitted, raw)
    expect(shouldApplyExternalRichHtml(emitted, raw, raw)).toBe(false)
  })

  it('применяет чужой incoming', () => {
    const emitted = new Set<string>()
    expect(shouldApplyExternalRichHtml(emitted, '<p>было</p>', '<p>стало</p>')).toBe(true)
  })
})
