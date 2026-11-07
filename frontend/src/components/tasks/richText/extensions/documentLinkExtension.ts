import { Node, mergeAttributes } from '@tiptap/core'

import { interceptRichTextLinkClick } from '@/utils/html/richTextLinkClick'

declare module '@tiptap/core' {
  interface Commands<ReturnType> {
    documentLink: {
      insertDocumentLink: (attrs: { documentId: string; documentTitle: string }) => ReturnType
    }
  }
}

/**
 * TipTap inline node — ярлык-ссылка на документ портала.
 *
 * В HTML сохраняется как:
 *   <a class="portal-doc-link" href="/documents/{id}" data-document-id="{id}">{title}</a>
 *
 * Санитайзер (sanitizeRichHtml.ts) явно разрешает такие href.
 */
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
    const { documentId, documentTitle } = node.attrs as {
      documentId: string | null
      documentTitle: string | null
    }
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

  addNodeView() {
    return ({ node }) => {
      const { documentId, documentTitle } = node.attrs as {
        documentId: string | null
        documentTitle: string | null
      }

      const dom = document.createElement('a')
      dom.className = 'portal-doc-link'
      dom.href = documentId ? `/documents/${documentId}` : '#'
      dom.setAttribute('data-document-id', documentId ?? '')
      dom.contentEditable = 'false'

      const icon = document.createElement('span')
      icon.className = 'portal-doc-link__icon'
      icon.setAttribute('aria-hidden', 'true')
      icon.textContent = '📄'

      const label = document.createElement('span')
      label.className = 'portal-doc-link__title'
      label.textContent = documentTitle || 'Документ'

      dom.appendChild(icon)
      dom.appendChild(label)

      dom.addEventListener('click', (e) => {
        interceptRichTextLinkClick(e)
      }, true)

      return { dom }
    }
  },

  addCommands() {
    return {
      insertDocumentLink:
        (attrs) =>
        ({ commands }) => {
          return commands.insertContent({
            type: this.name,
            attrs,
          })
        },
    }
  },
})
