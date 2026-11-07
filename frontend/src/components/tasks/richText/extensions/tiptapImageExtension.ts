import { Node, mergeAttributes, type Editor } from '@tiptap/core'

import { extractRichMediaIdsFromHtml, getRichMedia, richMediaFilePath } from '@/api/richMediaApi'
import { isDangerousHrefScheme } from '@/utils/html/richTextLinkClick'

import { openRichTextImageLightbox } from '../openRichTextImageLightbox'

type ImageAlign = 'left' | 'center' | 'right'

function mediaIdFromSrc(src: string | null | undefined): string | null {
  if (!src) return null
  const ids = extractRichMediaIdsFromHtml(src)
  return ids[0] ?? null
}

function resolveAndApplySrc(img: HTMLImageElement, src: string): () => void {
  const mediaId = mediaIdFromSrc(src)
  if (!mediaId) {
    // Не ставим опасные схемы (javascript:/data:) в img.src — security.mdc.
    if (!isDangerousHrefScheme(src)) img.src = src
    return () => { /* no-op */ }
  }
  let cancelled = false
  getRichMedia(mediaId)
    .then((m) => { if (!cancelled) img.src = m.download_url })
    .catch(() => { if (!cancelled && !isDangerousHrefScheme(src)) img.src = src })
  return () => { cancelled = true }
}

function parseWidthFromStyle(el: HTMLElement): string | null {
  const w = el.style.width
  return w && w !== 'auto' ? w : null
}

export const DocumentImage = Node.create({
  name: 'documentImage',
  group: 'block',
  atom: true,
  draggable: true,
  addAttributes() {
    return {
      src: { default: null },
      alt: { default: null },
      title: { default: null },
      align: {
        default: 'center',
        parseHTML: (el) => {
          const fig = el.closest?.('figure') ?? el.parentElement
          if (fig?.dataset.align && ['left', 'center', 'right'].includes(fig.dataset.align)) {
            return fig.dataset.align as ImageAlign
          }
          return 'center'
        },
      },
      width: {
        default: null,
        parseHTML: (el) => {
          const fig = el.closest?.('figure') ?? el.parentElement
          return fig ? parseWidthFromStyle(fig as HTMLElement) : null
        },
      },
    }
  },
  parseHTML() {
    return [
      { tag: 'figure.buildin-figure img[src]' },
      { tag: 'img.buildin-inline-image[src]' },
      { tag: 'img[src]' },
    ]
  },
  renderHTML({ HTMLAttributes }) {
    const { src, alt, title, align, width } = HTMLAttributes
    const figStyle = width ? `width:${width}` : undefined
    return [
      'figure',
      {
        class: 'buildin-figure',
        'data-align': align ?? 'center',
        ...(figStyle ? { style: figStyle } : {}),
      },
      [
        'img',
        mergeAttributes(
          { class: 'buildin-inline-image', loading: 'lazy' },
          { src, alt, title },
        ),
      ],
    ]
  },
  addNodeView() {
    return ({ node: initialNode, editor, getPos }) => {
      let cancelPrev: (() => void) | null = null
      let cancelResize: (() => void) | null = null
      let currentSrc = String(initialNode.attrs.src ?? '')

      /* Обёртка (drag-handle — только она) */
      const wrap = document.createElement('figure')
      wrap.className = 'buildin-figure-wrap'
      applyWrapAttrs(wrap, initialNode.attrs)

      const inner = document.createElement('figure')
      inner.className = 'buildin-figure'

      const img = document.createElement('img')
      img.className = 'buildin-inline-image'
      img.alt = String(initialNode.attrs.alt ?? '')
      if (initialNode.attrs.title) img.title = String(initialNode.attrs.title)
      img.loading = 'lazy'
      img.draggable = false

      cancelPrev = resolveAndApplySrc(img, currentSrc)

      img.style.cursor = 'zoom-in'
      img.addEventListener('click', (e) => {
        e.preventDefault()
        e.stopPropagation()
        if (img.src) openRichTextImageLightbox(img.src, img.alt)
      })

      const toolbar = document.createElement('div')
      toolbar.className = 'buildin-figure-toolbar'
      toolbar.setAttribute('contenteditable', 'false')

      const alignBtns: Array<{ align: ImageAlign; label: string }> = [
        { align: 'left', label: '←' },
        { align: 'center', label: '↔' },
        { align: 'right', label: '→' },
      ]
      for (const { align, label } of alignBtns) {
        const btn = document.createElement('button')
        btn.type = 'button'
        btn.className = 'buildin-figure-align-btn'
        btn.dataset.align = align
        btn.textContent = label
        btn.title = alignTitle(align)
        btn.setAttribute('aria-label', alignTitle(align))
        btn.addEventListener('mousedown', (e) => {
          e.preventDefault()
          e.stopPropagation()
          updateAttrs({ align })
        })
        toolbar.appendChild(btn)
      }

      const deleteBtn = document.createElement('button')
      deleteBtn.type = 'button'
      deleteBtn.className = 'buildin-figure-delete-btn'
      deleteBtn.setAttribute('aria-label', 'Удалить изображение')
      deleteBtn.title = 'Удалить изображение'
      deleteBtn.addEventListener('mousedown', (e) => {
        e.preventDefault()
        e.stopPropagation()
        const pos = getPos()
        if (pos === undefined) return
        editor.commands.command(({ tr }) => {
          tr.delete(pos, pos + 1)
          return true
        })
      })
      toolbar.appendChild(deleteBtn)

      /* Resize-handle */
      const handle = document.createElement('div')
      handle.className = 'buildin-figure-resize-handle'
      handle.setAttribute('contenteditable', 'false')
      cancelResize = attachResizeHandler(handle, wrap, img, updateAttrs)

      inner.appendChild(img)
      inner.appendChild(toolbar)
      inner.appendChild(handle)
      wrap.appendChild(inner)

      function updateAttrs(partial: Partial<{ align: ImageAlign; width: string | null }>) {
        const pos = getPos()
        if (pos === undefined) return
        const current = editor.state.doc.nodeAt(pos)
        if (!current) return
        editor.commands.command(({ tr }) => {
          tr.setNodeMarkup(pos, undefined, { ...current.attrs, ...partial })
          return true
        })
      }

      function syncToolbarActive(align: ImageAlign) {
        toolbar.querySelectorAll<HTMLButtonElement>('.buildin-figure-align-btn').forEach((btn) => {
          btn.classList.toggle('buildin-figure-align-btn--active', btn.dataset.align === align)
        })
      }

      syncToolbarActive((initialNode.attrs.align as ImageAlign) ?? 'center')

      return {
        dom: wrap,
        update(updatedNode) {
          if (updatedNode.type.name !== 'documentImage') return false

          const newSrc = String(updatedNode.attrs.src ?? '')
          if (newSrc !== currentSrc) {
            cancelPrev?.()
            currentSrc = newSrc
            cancelPrev = resolveAndApplySrc(img, newSrc)
          }
          img.alt = String(updatedNode.attrs.alt ?? '')
          if (updatedNode.attrs.title) {
            img.title = String(updatedNode.attrs.title)
          } else {
            img.removeAttribute('title')
          }
          applyWrapAttrs(wrap, updatedNode.attrs)
          syncToolbarActive((updatedNode.attrs.align as ImageAlign) ?? 'center')
          return true
        },
        destroy() {
          cancelPrev?.()
          cancelResize?.()
        },
      }
    }
  },
})

function alignTitle(align: ImageAlign): string {
  if (align === 'left') return 'По левому краю'
  if (align === 'right') return 'По правому краю'
  return 'По центру'
}

function applyWrapAttrs(wrap: HTMLElement, attrs: Record<string, unknown>) {
  const align = (attrs.align as ImageAlign) ?? 'center'
  const width = attrs.width as string | null | undefined
  wrap.dataset.align = align
  wrap.style.width = width ?? ''
}

function attachResizeHandler(
  handle: HTMLElement,
  wrap: HTMLElement,
  _img: HTMLImageElement,
  updateAttrs: (partial: { width: string }) => void,
): () => void {
  let activeCleanup: (() => void) | null = null
  handle.addEventListener('mousedown', (startEvent) => {
    startEvent.preventDefault()
    startEvent.stopPropagation()

    const startX = startEvent.clientX
    const startWidth = wrap.getBoundingClientRect().width

    function onMove(e: MouseEvent) {
      e.preventDefault()
      const delta = e.clientX - startX
      const newW = Math.max(80, Math.round(startWidth + delta))
      wrap.style.width = `${newW}px`
      wrap.style.maxWidth = '100%'
    }

    function onUp(e: MouseEvent) {
      document.removeEventListener('mousemove', onMove)
      document.removeEventListener('mouseup', onUp)
      activeCleanup = null
      const delta = e.clientX - startX
      const newW = Math.max(80, Math.round(startWidth + delta))
      updateAttrs({ width: `${newW}px` })
    }

    activeCleanup = () => {
      document.removeEventListener('mousemove', onMove)
      document.removeEventListener('mouseup', onUp)
    }
    document.addEventListener('mousemove', onMove)
    document.addEventListener('mouseup', onUp)
  })
  return () => {
    activeCleanup?.()
  }
}

export function insertDocumentImage(editor: Editor, src: string, alt = '') {
  editor
    .chain()
    .focus()
    .insertContent({
      type: 'documentImage',
      attrs: { src, alt },
    })
    .run()
}

export function insertDocumentImageAt(editor: Editor, pos: number, src: string, alt = ''): number {
  const node = editor.schema.nodes.documentImage.create({ src, alt })
  editor.commands.command(({ tr }) => {
    tr.insert(pos, node)
    return true
  })
  return pos + node.nodeSize
}

export function insertUploadedRichMediaAt(editor: Editor, pos: number, mediaId: string): number {
  return insertDocumentImageAt(editor, pos, richMediaFilePath(mediaId))
}
