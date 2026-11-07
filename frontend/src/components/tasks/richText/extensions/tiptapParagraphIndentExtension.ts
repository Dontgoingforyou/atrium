import { Extension } from '@tiptap/core'

const STEP_EM = 1.5
const MAX_LEVEL = 8

declare module '@tiptap/core' {
  interface Commands<ReturnType> {
    paragraphIndent: {
      indentParagraph: () => ReturnType
      outdentParagraph: () => ReturnType
    }
  }
}

function currentLevel(editor: { getAttributes: (name: string) => Record<string, unknown> }): number {
  if (editor.getAttributes('heading').indentLevel) {
    return Number(editor.getAttributes('heading').indentLevel) || 0
  }
  return Number(editor.getAttributes('paragraph').indentLevel) || 0
}

/** Отступ абзаца/заголовка (не только списки). */
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
              return Math.round(Number(match[1]) / STEP_EM)
            },
            renderHTML: (attributes) => {
              const level = Number(attributes.indentLevel) || 0
              if (level <= 0) return {}
              return { style: `margin-left: ${level * STEP_EM}em` }
            },
          },
        },
      },
    ]
  },
  addCommands() {
    return {
      indentParagraph:
        () =>
        ({ editor, chain }) => {
          if (editor.isActive('taskItem')) {
            return chain().focus().sinkListItem('taskItem').run()
          }
          if (editor.isActive('listItem')) {
            return chain().focus().sinkListItem('listItem').run()
          }
          const level = currentLevel(editor)
          if (level >= MAX_LEVEL) return false
          const next = level + 1
          if (editor.isActive('heading')) {
            return chain().focus().updateAttributes('heading', { indentLevel: next }).run()
          }
          return chain().focus().updateAttributes('paragraph', { indentLevel: next }).run()
        },
      outdentParagraph:
        () =>
        ({ editor, chain }) => {
          if (editor.isActive('taskItem')) {
            return chain().focus().liftListItem('taskItem').run()
          }
          if (editor.isActive('listItem')) {
            return chain().focus().liftListItem('listItem').run()
          }
          const level = currentLevel(editor)
          if (level <= 0) return false
          const next = level - 1
          if (editor.isActive('heading')) {
            return chain().focus().updateAttributes('heading', { indentLevel: next }).run()
          }
          return chain().focus().updateAttributes('paragraph', { indentLevel: next }).run()
        },
    }
  },
})
