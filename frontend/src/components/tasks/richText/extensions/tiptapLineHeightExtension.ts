import { Extension } from '@tiptap/core'

declare module '@tiptap/core' {
  interface Commands<ReturnType> {
    lineHeight: {
      setLineHeight: (value: string) => ReturnType
      unsetLineHeight: () => ReturnType
    }
  }
}

/** Межстрочный интервал на абзацах и заголовках. */
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
              const lh = attributes.lineHeight as string | null | undefined
              if (!lh || !/^\d+(\.\d+)?$/.test(lh)) {
                return {}
              }
              return { style: `line-height: ${lh}` }
            },
          },
        },
      },
    ]
  },
  addCommands() {
    return {
      setLineHeight:
        (lineHeight: string) =>
        ({ chain, editor }) => {
          if (editor.isActive('heading')) {
            return chain().focus().updateAttributes('heading', { lineHeight }).run()
          }
          return chain().focus().updateAttributes('paragraph', { lineHeight }).run()
        },
      unsetLineHeight:
        () =>
        ({ chain, editor }) => {
          if (editor.isActive('heading')) {
            return chain().focus().updateAttributes('heading', { lineHeight: null }).run()
          }
          return chain().focus().updateAttributes('paragraph', { lineHeight: null }).run()
        },
    }
  },
})
