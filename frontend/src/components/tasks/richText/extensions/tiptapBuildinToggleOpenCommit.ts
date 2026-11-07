import type { Editor } from '@tiptap/core'

const openCommitTimers = new Map<number, ReturnType<typeof setTimeout>>()
const pendingOpenByPos = new Map<number, boolean>()

export function applyToggleNodeAttrs(
  editor: Editor,
  pos: number,
  attrs: { title: string; open: boolean },
): void {
  const current = editor.state.doc.nodeAt(pos)
  if (!current || current.type.name !== 'buildinToggle') return
  if (current.attrs.title === attrs.title && Boolean(current.attrs.open) === attrs.open) {
    return
  }
  editor.commands.command(({ tr }) => {
    tr.setNodeMarkup(pos, undefined, { ...current.attrs, ...attrs })
    return true
  })
}

export function peekPendingToggleOpen(pos: number): boolean | undefined {
  return pendingOpenByPos.get(pos)
}

export function scheduleToggleOpenAttr(
  editor: Editor,
  pos: number,
  open: boolean,
  delayMs: number,
  title?: string,
): void {
  const prev = openCommitTimers.get(pos)
  if (prev !== undefined) {
    clearTimeout(prev)
    openCommitTimers.delete(pos)
  }
  pendingOpenByPos.set(pos, open)
  const run = () => {
    openCommitTimers.delete(pos)
    pendingOpenByPos.delete(pos)
    const node = editor.state.doc.nodeAt(pos)
    if (!node || node.type.name !== 'buildinToggle') return
    applyToggleNodeAttrs(editor, pos, {
      title: title ?? String(node.attrs.title ?? ''),
      open,
    })
  }
  if (delayMs === 0) {
    run()
    return
  }
  openCommitTimers.set(pos, setTimeout(run, delayMs))
}
