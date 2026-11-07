import { Extension } from '@tiptap/core'

export const TabHandler = Extension.create({
  name: 'tabHandler',
  addKeyboardShortcuts() {
    return {
      Tab: ({ editor }) => {
        if (editor.isActive('taskItem')) {
          return editor.commands.sinkListItem('taskItem')
        }
        if (editor.isActive('listItem')) {
          return editor.commands.sinkListItem('listItem')
        }
        return editor.commands.indentParagraph()
      },
      'Shift-Tab': ({ editor }) => {
        if (editor.isActive('taskItem')) {
          return editor.commands.liftListItem('taskItem')
        }
        if (editor.isActive('listItem')) {
          return editor.commands.liftListItem('listItem')
        }
        return editor.commands.outdentParagraph()
      },
    }
  },
})
