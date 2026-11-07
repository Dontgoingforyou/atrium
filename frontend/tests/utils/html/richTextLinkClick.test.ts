// @vitest-environment jsdom

import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  interceptRichTextLinkClick,
  isRichTextLinkHrefAllowed,
  openRichTextLink,
} from '@/utils/html/richTextLinkClick'
import { registerSpaNavigate } from '@/utils/spaNavigate'

describe('isRichTextLinkHrefAllowed', () => {
  it('allows https and same-origin paths', () => {
    expect(isRichTextLinkHrefAllowed('https://example.com/page')).toBe(true)
    expect(isRichTextLinkHrefAllowed('/tasks/1')).toBe(true)
  })

  it('rejects javascript and data URLs', () => {
    expect(isRichTextLinkHrefAllowed('javascript:alert(1)')).toBe(false)
    expect(isRichTextLinkHrefAllowed('data:text/html,x')).toBe(false)
    expect(isRichTextLinkHrefAllowed('')).toBe(false)
  })

  it('rejects mixed-case and leading-whitespace dangerous schemes', () => {
    expect(isRichTextLinkHrefAllowed('JavaScript:alert(1)')).toBe(false)
    expect(isRichTextLinkHrefAllowed('  javascript:alert(1)')).toBe(false)
    expect(isRichTextLinkHrefAllowed('DATA:text/html,x')).toBe(false)
    expect(isRichTextLinkHrefAllowed('  Data:text/html,x')).toBe(false)
  })
})

describe('openRichTextLink', () => {
  afterEach(() => {
    registerSpaNavigate(() => undefined)
    vi.restoreAllMocks()
  })

  it('navigates same-origin document links in the same tab via SPA', () => {
    const navigate = vi.fn()
    registerSpaNavigate(navigate)
    const openSpy = vi.spyOn(window, 'open').mockImplementation(() => null)

    expect(openRichTextLink('/documents/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee')).toBe(true)
    expect(navigate).toHaveBeenCalledWith('/documents/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee')
    expect(openSpy).not.toHaveBeenCalled()
  })

  it('ignores hash-only href', () => {
    const navigate = vi.fn()
    registerSpaNavigate(navigate)
    expect(openRichTextLink('#')).toBe(false)
    expect(navigate).not.toHaveBeenCalled()
  })
})

describe('interceptRichTextLinkClick', () => {
  afterEach(() => {
    registerSpaNavigate(() => undefined)
    document.body.replaceChildren()
    vi.restoreAllMocks()
  })

  function makeEvent(href: string, init: MouseEventInit = {}) {
    const a = document.createElement('a')
    a.setAttribute('href', href)
    a.setAttribute('target', '_blank')
    a.className = 'portal-doc-link'
    document.body.appendChild(a)
    const event = new MouseEvent('click', { bubbles: true, cancelable: true, ...init })
    Object.defineProperty(event, 'target', { value: a })
    return event
  }

  it('обычный клик по ярлыку документа — только SPA, без новой вкладки', () => {
    const navigate = vi.fn()
    registerSpaNavigate(navigate)
    const openSpy = vi.spyOn(window, 'open').mockImplementation(() => null)
    const event = makeEvent('/documents/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee')
    expect(interceptRichTextLinkClick(event)).toBe(true)
    expect(event.defaultPrevented).toBe(true)
    expect(navigate).toHaveBeenCalledTimes(1)
    expect(navigate).toHaveBeenCalledWith('/documents/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee')
    expect(openSpy).not.toHaveBeenCalled()
  })

  it('глушит javascript: и не открывает схему', () => {
    const openSpy = vi.spyOn(window, 'open').mockImplementation(() => null)
    const event = makeEvent('javascript:alert(1)')
    expect(interceptRichTextLinkClick(event)).toBe(true)
    expect(event.defaultPrevented).toBe(true)
    expect(openSpy).not.toHaveBeenCalled()
  })

  it('не глушит native, если переход не удался', () => {
    const navigate = vi.fn()
    registerSpaNavigate(navigate)
    const event = makeEvent('#section')
    expect(interceptRichTextLinkClick(event)).toBe(false)
    expect(event.defaultPrevented).toBe(false)
    expect(navigate).not.toHaveBeenCalled()
  })

  it('Ctrl/Cmd-клик не дублирует переход через SPA', () => {
    const navigate = vi.fn()
    registerSpaNavigate(navigate)
    const openSpy = vi.spyOn(window, 'open').mockImplementation(() => null)
    const event = makeEvent('/documents/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee', { ctrlKey: true })
    expect(interceptRichTextLinkClick(event)).toBe(false)
    expect(event.defaultPrevented).toBe(false)
    expect(navigate).not.toHaveBeenCalled()
    expect(openSpy).not.toHaveBeenCalled()
  })
})
