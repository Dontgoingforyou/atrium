import type { Editor } from '@tiptap/react'

/** Включает один тип списка, снимая остальные (без вложенного bullet + checklist). */
export function toggleExclusiveList(
  editor: Editor,
  kind: 'taskList' | 'bulletList' | 'orderedList',
): void {
  const chain = editor.chain().focus()
  if (kind !== 'bulletList' && editor.isActive('bulletList')) {
    chain.toggleBulletList()
  }
  if (kind !== 'orderedList' && editor.isActive('orderedList')) {
    chain.toggleOrderedList()
  }
  if (kind !== 'taskList' && editor.isActive('taskList')) {
    chain.toggleTaskList()
  }
  if (kind === 'taskList') chain.toggleTaskList()
  if (kind === 'bulletList') chain.toggleBulletList()
  if (kind === 'orderedList') chain.toggleOrderedList()
  chain.run()
}
