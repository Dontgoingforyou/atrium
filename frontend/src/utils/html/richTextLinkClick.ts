import type { MouseEvent, PointerEvent } from 'react'

import { isSafeExternalUrl, openExternalUrl } from '../safeExternalUrl'
import { spaNavigate } from '../spaNavigate'

/** Опасные схемы href, которые не должны открываться (XSS). Сравнение case-insensitive. */
export function isDangerousHrefScheme(href: string): boolean {
  const normalized = href.trim().toLowerCase()
  return normalized.startsWith('javascript:') || normalized.startsWith('data:')
}

/** Не даём dnd-kit перехватить pointer при клике по ссылке в rich-text. */
export function stopPointerOnRichTextLink(e: PointerEvent<HTMLElement>): void {
  if ((e.target as HTMLElement).closest('a')) {
    e.stopPropagation()
  }
}

export function openRichTextLink(href: string): boolean {
  if (!href || isDangerousHrefScheme(href)) {
    return false
  }
  if (href === '#' || href.startsWith('#')) {
    return false
  }
  try {
    const url = new URL(href, window.location.origin)
    if (url.origin === window.location.origin) {
      const next = `${url.pathname}${url.search}${url.hash}`
      const cur = `${window.location.pathname}${window.location.search}${window.location.hash}`
      if (next === cur) {
        return true
      }
      spaNavigate(next)
      return true
    }
  } catch {
    return false
  }
  return openExternalUrl(href)
}

/** DOM-клик и React SyntheticEvent — оба подходят (не путать с DOM Event). */
type RichTextLinkClickEvent = {
  target: EventTarget | null
  button?: number
  ctrlKey?: boolean
  metaKey?: boolean
  shiftKey?: boolean
  altKey?: boolean
  preventDefault: () => void
  stopPropagation: () => void
  stopImmediatePropagation?: () => void
}

function isModifiedLinkClick(event: RichTextLinkClickEvent): boolean {
  return (
    (event.button ?? 0) !== 0 ||
    Boolean(event.ctrlKey || event.metaKey || event.shiftKey || event.altKey)
  )
}

/**
 * Обычный клик по `<a>`: глушим native (в т.ч. target=_blank) и открываем сами.
 * Ctrl/Cmd/Shift/средняя кнопка — не трогаем, чтобы не открыть и текущую, и новую вкладку.
 */
export function interceptRichTextLinkClick(event: RichTextLinkClickEvent): boolean {
  const target = event.target
  if (!(target instanceof Element)) return false
  const anchor = target.closest('a')
  if (!anchor) return false
  if (isModifiedLinkClick(event)) return false
  const href = anchor.getAttribute('href') ?? ''
  if (!href || isDangerousHrefScheme(href)) {
    event.preventDefault()
    event.stopPropagation()
    event.stopImmediatePropagation?.()
    return true
  }
  const opened = openRichTextLink(href)
  if (!opened) return false
  event.preventDefault()
  event.stopPropagation()
  event.stopImmediatePropagation?.()
  return true
}

/**
 * Клик по rich-text: внутренние ссылки — SPA, внешние — новая вкладка.
 */
export function handleRichTextContainerClick(
  e: MouseEvent<HTMLElement>,
  onDefault?: () => void,
): void {
  const target = e.target
  if (target instanceof Element && target.closest('a')) {
    interceptRichTextLinkClick(e)
    return
  }
  onDefault?.()
}

export function isRichTextLinkHrefAllowed(href: string): boolean {
  if (!href || isDangerousHrefScheme(href)) {
    return false
  }
  try {
    const url = new URL(href, window.location.origin)
    if (url.origin === window.location.origin) return true
    return isSafeExternalUrl(href)
  } catch {
    return false
  }
}
