import { Node, mergeAttributes } from '@tiptap/core'
import type { Editor } from '@tiptap/core'
import { NodeSelection, TextSelection } from '@tiptap/pm/state'

import { buildinToggleBodyHasContent, buildinToggleInsertAttrs } from '@/domain/documents/buildinToggle'
import {
  caretPosInFirstToggleBodyBlock,
  resolveInsertedBuildinTogglePos,
  shouldProtectBuildinToggleFromKeyboardDelete,
} from '@/domain/documents/buildinToggleSelection'
import { parseBuildinToggleTitle } from '@/domain/documents/buildinToggleTitle'

import { createBuildinToggleNodeView } from './tiptapBuildinToggleNodeView'

export { shouldProtectBuildinToggleFromKeyboardDelete }

declare module '@tiptap/core' {
  interface Commands<ReturnType> {
    buildinToggle: {
      insertBuildinToggle: () => ReturnType
      deleteBuildinToggle: () => ReturnType
    }
  }
}

/**
 * Раскрывающийся блок (toggle) из импорта BuildIn.
 * NodeView: стрелка (click → toggle) + input заголовка; тело — ProseMirror.
 */
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
          return buildinToggleBodyHasContent(element.querySelector('.buildin-toggle-body'))
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
        contentElement: (node: HTMLElement) =>
          (node.querySelector('.buildin-toggle-body') as HTMLElement | null) ?? node,
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

  addCommands() {
    return {
      insertBuildinToggle:
        () =>
        ({ chain }) =>
          chain()
            .insertContent({
              type: this.name,
              attrs: buildinToggleInsertAttrs(),
              content: [{ type: 'paragraph' }],
            })
            .command(({ state, dispatch }) => {
              const sel = state.selection
              const togglePos = resolveInsertedBuildinTogglePos({
                $from: sel.$from,
                selectedNodeName: sel instanceof NodeSelection ? sel.node.type.name : null,
                selectedNodePos: sel instanceof NodeSelection ? sel.from : null,
              })
              if (togglePos == null) return true
              const caret = caretPosInFirstToggleBodyBlock(togglePos)
              if (dispatch) {
                dispatch(state.tr.setSelection(TextSelection.create(state.doc, caret)))
              }
              return true
            })
            .run(),
      deleteBuildinToggle:
        () =>
        ({ state, dispatch }) => {
          const { $from } = state.selection
          for (let depth = $from.depth; depth > 0; depth -= 1) {
            const node = $from.node(depth)
            if (node.type.name !== 'buildinToggle') continue
            const pos = $from.before(depth)
            if (dispatch) {
              const tr = state.tr.delete(pos, pos + node.nodeSize)
              dispatch(tr)
            }
            return true
          }
          return false
        },
    }
  },

  addKeyboardShortcuts() {
    const protectToggleAtStart = ({ editor }: { editor: Editor }): boolean => {
      if (!shouldProtectBuildinToggleFromKeyboardDelete(editor.state.selection)) return false
      return true
    }
    return {
      Backspace: protectToggleAtStart,
      Delete: protectToggleAtStart,
    }
  },

  addNodeView() {
    return (props) => createBuildinToggleNodeView(props)
  },
})
