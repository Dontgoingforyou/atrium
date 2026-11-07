import type { CommandProps } from '@tiptap/core'
import { Table } from '@tiptap/extension-table'
import { TableCell } from '@tiptap/extension-table-cell'
import { TableHeader } from '@tiptap/extension-table-header'
import { TableRow } from '@tiptap/extension-table-row'
import { columnResizingPluginKey, isInTable, moveTableColumn, selectedRect } from '@tiptap/pm/tables'
import { DecorationSet } from '@tiptap/pm/view'
import type { Plugin } from '@tiptap/pm/state'

import { TableRowResize } from './tiptapTableRowResize'

declare module '@tiptap/core' {
  interface Commands<ReturnType> {
    portalTableColumn: {
      moveColumnLeft: () => ReturnType
      moveColumnRight: () => ReturnType
    }
  }
}

function moveCurrentColumn(direction: -1 | 1) {
  return ({ state, dispatch }: CommandProps) => {
    if (!isInTable(state)) return false
    let from = 0
    let width = 0
    try {
      const rect = selectedRect(state)
      if (rect.right - rect.left !== 1) return false
      from = rect.left
      width = rect.map.width
    } catch {
      return false
    }
    const to = from + direction
    if (to < 0 || to >= width) return false
    try {
      return moveTableColumn({ from, to })(state, dispatch)
    } catch {
      return false
    }
  }
}

/** Тип для доступа к приватным полям Plugin, не раскрытым в публичных .d.ts. */
type PluginInternals = Plugin & {
  spec?: { key?: unknown }
  props: { decorations?: unknown }
}

export const PortalTable = Table.extend({
  addAttributes() {
    return {
      ...this.parent?.(),
      class: {
        default: 'portal-rich-table',
        parseHTML: (element) => element.getAttribute('class'),
        renderHTML: (attributes) => {
          if (!attributes.class) {
            return {}
          }
          return { class: attributes.class }
        },
      },
    }
  },

  addProseMirrorPlugins() {
    const plugins = this.parent?.() ?? []
    for (const plugin of plugins) {
      const internals = plugin as PluginInternals
      if (internals.spec?.key !== columnResizingPluginKey) continue
      internals.props.decorations = () => DecorationSet.empty
    }
    return plugins
  },

  addCommands() {
    return {
      ...this.parent?.(),
      moveColumnLeft: () => moveCurrentColumn(-1),
      moveColumnRight: () => moveCurrentColumn(1),
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
          const h = (element as HTMLElement).style?.height
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
  PortalTable.configure({
    resizable: true,
    handleWidth: 8,
    cellMinWidth: 48,
    lastColumnResizable: true,
  }),
  PortalTableRow,
  TableHeader,
  TableCell,
  TableRowResize,
]
