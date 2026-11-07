import DOMPurify from 'dompurify'

import { resolveRichMediaUrlsInHtml } from '@/api/richMediaApi'

/**
 * Разрешённые CSS-свойства в style-атрибутах rich-text контента.
 *
 * Список ограничен только свойствами, которые использует редактор (TipTap).
 * Все остальные удаляются для исключения CSS-инъекций
 * (background-image для tracking-пикселей, pointer-events для UI-манипуляций и др.).
 */
const ALLOWED_CSS_PROPERTIES = new Set([
  'font-size',
  'color',
  'text-align',
  'font-weight',
  'font-style',
  'text-decoration',
  'background-color',
  'font-family',
  'line-height',
  'margin-left',
  'width',
  'height',
])

/**
 * Классы, которые TipTap сериализует в HTML контента.
 * Остальные (в т.ч. lightbox/overlay) снимаются — иначе UI-spoof через dangerouslySetInnerHTML.
 */
const ALLOWED_CLASS_RE = /^(buildin-|portal-doc-link)/

const RICH_MEDIA_SRC_RE = /^\/api\/v1\/portal\/rich-media\/[0-9a-f-]{36}\/file$/i

/** Разрешённый формат href для ярлыков-ссылок на документы портала. */
const PORTAL_DOC_HREF_RE = /^\/documents\/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

/** Регистрируем afterSanitizeAttributes-хук один раз на процесс (защита от HMR/повторного импорта). */
let sanitizeHookRegistered = false
function ensureSanitizeHookRegistered(): void {
  if (sanitizeHookRegistered) return
  sanitizeHookRegistered = true
  DOMPurify.addHook('afterSanitizeAttributes', (node) => {
    if (node instanceof Element && node.hasAttribute('style')) {
      stripDisallowedCssProperties(node)
      stripSpoofingCssValues(node)
    }
    if (node instanceof Element && node.hasAttribute('class')) {
      filterAllowedClasses(node)
    }
    if (node instanceof HTMLAnchorElement) {
      const href = node.getAttribute('href') ?? ''
      if (href.startsWith('javascript:') || href.startsWith('data:')) {
        node.removeAttribute('href')
      } else if (PORTAL_DOC_HREF_RE.test(href)) {
        // Внутренние ссылки на документы портала — открываем в той же вкладке через React Router
        node.removeAttribute('target')
        node.removeAttribute('rel')
      } else if (href) {
        try {
          const url = new URL(href, 'https://example.invalid')
          if (url.protocol === 'http:' || url.protocol === 'https:') {
            node.setAttribute('target', '_blank')
            node.setAttribute('rel', 'noopener noreferrer')
          }
        } catch {
          node.removeAttribute('href')
        }
      }
    }
    if (node instanceof HTMLImageElement) {
      const src = node.getAttribute('src') ?? ''
      if (!isAllowedImgSrc(src)) {
        node.removeAttribute('src')
      }
    }
  })
}

function isAllowedImgSrc(src: string): boolean {
  if (!src) return false
  // case-insensitive + trim: DOMPurify нормализует, но защита в хуке должна быть устойчивой
  // к `DATA:`, ` JavaScript:` и вариантам с ведущими пробелами/переносами.
  const normalized = src.trim().toLowerCase()
  if (normalized.startsWith('data:') || normalized.startsWith('javascript:')) {
    return false
  }
  if (RICH_MEDIA_SRC_RE.test(src)) {
    return true
  }
  try {
    const u = new URL(src, window.location.origin)
    if (u.protocol === 'https:') return true
    if (u.origin === window.location.origin && RICH_MEDIA_SRC_RE.test(u.pathname)) {
      return true
    }
  } catch {
    return false
  }
  return false
}

function filterAllowedClasses(element: Element): void {
  const raw = element.getAttribute('class') ?? ''
  const kept = raw
    .split(/\s+/)
    .map((c) => c.trim())
    .filter((c) => c.length > 0 && ALLOWED_CLASS_RE.test(c))
  if (kept.length === 0) {
    element.removeAttribute('class')
  } else {
    element.setAttribute('class', kept.join(' '))
  }
}

function stripDisallowedCssProperties(element: Element): void {
  const style = (element as HTMLElement).style
  if (!style || style.length === 0) return
  const toRemove: string[] = []
  for (let i = 0; i < style.length; i++) {
    const prop = style.item(i)
    if (!ALLOWED_CSS_PROPERTIES.has(prop)) {
      toRemove.push(prop)
    }
  }
  for (const prop of toRemove) {
    style.removeProperty(prop)
  }
  if (style.length === 0) {
    element.removeAttribute('style')
  }
}

/** Скрытый кликабельный текст / нулевой кегль — UI-spoof в read-only HTML. */
function stripSpoofingCssValues(element: Element): void {
  const style = (element as HTMLElement).style
  if (!style || style.length === 0) return

  const color = style.getPropertyValue('color').trim().toLowerCase()
  if (
    color === 'transparent' ||
    color === 'rgba(0, 0, 0, 0)' ||
    color === 'rgba(0,0,0,0)' ||
    color === 'hsla(0, 0%, 0%, 0)' ||
    color === 'hsla(0,0%,0%,0)'
  ) {
    style.removeProperty('color')
  }

  const fontSize = style.getPropertyValue('font-size').trim().toLowerCase()
  if (fontSize === '0' || fontSize === '0px' || fontSize === '0pt' || fontSize === '0em' || fontSize === '0rem') {
    style.removeProperty('font-size')
  }

  if (style.length === 0) {
    element.removeAttribute('style')
  }
}

export function sanitizeRichHtml(html: string): string {
  ensureSanitizeHookRegistered()
  return DOMPurify.sanitize(html, {
    ADD_ATTR: [
      'style',
      'loading',
      'class',
      'data-align',
      'data-document-id',
      'data-colwidth',
      'colspan',
      'rowspan',
    ],
    ADD_TAGS: ['details', 'summary', 'figure', 'img', 'mark'],
  })
}

/** Для просмотра: presigned URL + санитизация. */
export async function prepareRichHtmlForDisplay(html: string): Promise<string> {
  if (!html.trim()) return ''
  const resolved = await resolveRichMediaUrlsInHtml(html)
  return sanitizeRichHtml(resolved)
}
