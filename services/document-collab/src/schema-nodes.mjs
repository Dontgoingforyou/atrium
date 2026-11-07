/**
 * Schema-only копии кастомных нод/атрибутов фронтового RichTextEditor.
 * Без NodeView, горячих клавиш и DOM-плагинов — только parseHTML/renderHTML.
 */
import { Extension, Node, mergeAttributes } from '@tiptap/core'
import { Table } from '@tiptap/extension-table'
import { TableCell } from '@tiptap/extension-table-cell'
import { TableHeader } from '@tiptap/extension-table-header'
import { TableRow } from '@tiptap/extension-table-row'

import { parseBuildinToggleTitle } from './parse-buildin-toggle-title.mjs'

const INDENT_STEP_EM = 1.5

export const FontSize = Extension.create({
  name: 'fontSize',
  addOptions() {
    return { types: ['textStyle'] }
  },
  addGlobalAttributes() {
    return [
      {
        types: this.options.types,
        attributes: {
          fontSize: {
            default: null,
            parseHTML: (element) => element.style.fontSize?.replace(/['"]+/g, '') || null,
            renderHTML: (attributes) => {
              if (!attributes.fontSize) return {}
              const safeSize = /^\d+px$/.test(String(attributes.fontSize))
                ? attributes.fontSize
                : null
              if (!safeSize) return {}
              return { style: `font-size: ${safeSize}` }
            },
          },
        },
      },
    ]
  },
})

export const LineHeight = Extension.create({
  name: 'lineHeight',
  addGlobalAttributes() {
    return [
      {
        types: ['paragraph', 'heading'],
        attributes: {
          lineHeight: {
            default: null,
            parseHTML: (element) => element.style.lineHeight || null,
            renderHTML: (attributes) => {
              const lh = attributes.lineHeight
              if (!lh || !/^\d+(\.\d+)?$/.test(lh)) return {}
              return { style: `line-height: ${lh}` }
            },
          },
        },
      },
    ]
  },
})

export const ParagraphIndent = Extension.create({
  name: 'paragraphIndent',
  addGlobalAttributes() {
    return [
      {
        types: ['paragraph', 'heading'],
        attributes: {
          indentLevel: {
            default: 0,
            parseHTML: (element) => {
              const ml = element.style.marginLeft
              if (!ml) return 0
              const match = /^([\d.]+)em$/.exec(ml)
              if (!match) return 0
              return Math.round(Number(match[1]) / INDENT_STEP_EM)
            },
            renderHTML: (attributes) => {
              const level = Number(attributes.indentLevel) || 0
              if (level <= 0) return {}
              return { style: `margin-left: ${level * INDENT_STEP_EM}em` }
            },
          },
        },
      },
    ]
  },
})

export const BuildinToggle = Node.create({
  name: 'buildinToggle',
  group: 'block',
  content: 'block+',
  defining: true,
  isolating: true,
  addAttributes() {
    return {
      title: {
        default: '',
        parseHTML: (element) => parseBuildinToggleTitle(element),
        renderHTML: () => ({}),
      },
      open: {
        default: false,
        parseHTML: (element) => {
          if (element.hasAttribute('open')) return true
          return Boolean(element.querySelector('.buildin-toggle-body')?.textContent?.trim())
        },
        renderHTML: (attributes) => (attributes.open ? { open: 'open' } : {}),
      },
    }
  },
  parseHTML() {
    return [
      {
        tag: 'details.buildin-toggle',
        priority: 80,
        contentElement: (node) => node.querySelector('.buildin-toggle-body') ?? node,
      },
    ]
  },
  renderHTML({ node, HTMLAttributes }) {
    return [
      'details',
      mergeAttributes(HTMLAttributes, {
        class: 'buildin-toggle',
        ...(node.attrs.open ? { open: 'open' } : {}),
      }),
      ['summary', {}, String(node.attrs.title ?? '')],
      ['div', { class: 'buildin-toggle-body' }, 0],
    ]
  },
})

export const DocumentImage = Node.create({
  name: 'documentImage',
  group: 'block',
  atom: true,
  addAttributes() {
    return {
      src: { default: null },
      alt: { default: null },
      title: { default: null },
      align: {
        default: 'center',
        parseHTML: (el) => {
          const fig = el.closest?.('figure') ?? el.parentElement
          if (fig?.dataset?.align && ['left', 'center', 'right'].includes(fig.dataset.align)) {
            return fig.dataset.align
          }
          return 'center'
        },
      },
      width: {
        default: null,
        parseHTML: (el) => {
          const fig = el.closest?.('figure') ?? el.parentElement
          const w = fig?.style?.width
          return w && w !== 'auto' ? w : null
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
      ['img', mergeAttributes({ class: 'buildin-inline-image', loading: 'lazy' }, { src, alt, title })],
    ]
  },
})

export const DocumentLink = Node.create({
  name: 'documentLink',
  group: 'inline',
  inline: true,
  atom: true,
  addAttributes() {
    return {
      documentId: {
        default: null,
        parseHTML: (el) => el.getAttribute('data-document-id'),
        renderHTML: (attrs) => ({ 'data-document-id': attrs.documentId }),
      },
      documentTitle: {
        default: null,
        parseHTML: (el) => el.textContent?.trim() || null,
        renderHTML: () => ({}),
      },
    }
  },
  parseHTML() {
    return [{ tag: 'a[data-document-id]' }]
  },
  renderHTML({ node, HTMLAttributes }) {
    const { documentId, documentTitle } = node.attrs
    const title = documentTitle || 'Документ'
    return [
      'a',
      mergeAttributes(HTMLAttributes, {
        class: 'portal-doc-link',
        href: documentId ? `/documents/${documentId}` : '#',
        'data-document-id': documentId,
      }),
      title,
    ]
  },
})

export const PortalTable = Table.extend({
  addAttributes() {
    return {
      ...this.parent?.(),
      class: {
        default: 'portal-rich-table',
        parseHTML: (element) => element.getAttribute('class'),
        renderHTML: (attributes) => {
          if (!attributes.class) return {}
          return { class: attributes.class }
        },
      },
    }
  },
})

export const PortalTableRow = TableRow.extend({
  addAttributes() {
    return {
      ...this.parent?.(),
      height: {
        default: null,
        parseHTML: (element) => {
          const h = element.style?.height
          return h && h !== 'auto' ? h : null
        },
        renderHTML: (attributes) => {
          if (!attributes.height) return {}
          return { style: `height: ${attributes.height}` }
        },
      },
    }
  },
})

export const portalTableExtensions = [
  PortalTable.configure({ resizable: false }),
  PortalTableRow,
  TableHeader,
  TableCell,
]
