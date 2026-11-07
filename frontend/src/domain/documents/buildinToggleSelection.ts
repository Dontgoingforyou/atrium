export function isCaretInsideNode(caret: number, nodeStart: number, nodeSize: number): boolean {
  return caret > nodeStart && caret < nodeStart + nodeSize
}

export function findBuildinToggleDepth($from: {
  depth: number
  node: (depth: number) => { type: { name: string } }
}): number | null {
  for (let depth = $from.depth; depth > 0; depth -= 1) {
    if ($from.node(depth).type.name === 'buildinToggle') return depth
  }
  return null
}

type ToggleResolvedPos = {
  depth: number
  parentOffset: number
  pos: number
  node: (depth: number) => { type: { name: string } }
  before: (depth: number) => number
  nodeBefore: { type: { name: string }; nodeSize: number } | null
}

export function shouldProtectBuildinToggleFromKeyboardDelete(selection: {
  empty: boolean
  $from: Pick<ToggleResolvedPos, 'depth' | 'parentOffset' | 'node' | 'before'>
}): boolean {
  if (!selection.empty) return false
  const { $from } = selection
  const toggleDepth = findBuildinToggleDepth($from)
  if (toggleDepth == null) return false
  const togglePos = $from.before(toggleDepth)
  return $from.parentOffset === 0 && $from.before($from.depth) === togglePos + 1
}

export function caretPosInFirstToggleBodyBlock(togglePos: number): number {
  return togglePos + 2
}

export function resolveInsertedBuildinTogglePos(params: {
  $from: Pick<ToggleResolvedPos, 'depth' | 'pos' | 'node' | 'before' | 'nodeBefore'>
  selectedNodeName: string | null
  selectedNodePos: number | null
}): number | null {
  const depth = findBuildinToggleDepth(params.$from)
  if (depth != null) return params.$from.before(depth)
  if (params.selectedNodeName === 'buildinToggle' && params.selectedNodePos != null) {
    return params.selectedNodePos
  }
  const before = params.$from.nodeBefore
  if (before?.type.name === 'buildinToggle') {
    return params.$from.pos - before.nodeSize
  }
  return null
}

export function shouldSyncPmSelectionFromNative(params: {
  nativeInsideContentDom: boolean
  mappedFrom: number | null
  mappedTo: number | null
  togglePos: number | null
  toggleSize: number
  pmFrom: number
  pmTo: number
}): boolean {
  if (!params.nativeInsideContentDom) return false
  if (params.mappedFrom == null || params.mappedTo == null || params.togglePos == null) return false
  if (!isCaretInsideNode(params.mappedFrom, params.togglePos, params.toggleSize)) return false
  if (!isCaretInsideNode(params.mappedTo, params.togglePos, params.toggleSize)) return false
  return params.pmFrom !== params.mappedFrom || params.pmTo !== params.mappedTo
}

export function toggleBodyContentEditable(editable: boolean): 'true' | 'false' {
  return editable ? 'true' : 'false'
}

export function shouldSyncToggleSelectionOnKey(key: string): boolean {
  return (
    key === 'Enter' ||
    key === 'Backspace' ||
    key === 'Delete' ||
    key === 'Home' ||
    key === 'End' ||
    key.startsWith('Arrow')
  )
}

/**
 * После Enter PM уже в новом абзаце, native-каретка часто остаётся в старом text node.
 * Зеркало: DOM ← PM через domAtPos, не view.focus().
 */
export function shouldFollowPmCaretAfterKey(key: string): boolean {
  return key === 'Enter'
}

export function shouldInterceptToggleBodyEnter(event: {
  shiftKey: boolean
  ctrlKey: boolean
  metaKey: boolean
  altKey: boolean
  isComposing: boolean
}): boolean {
  return !event.shiftKey && !event.ctrlKey && !event.metaKey && !event.altKey && !event.isComposing
}

export function shouldApplyNativeSelectionFromPm(params: {
  pmInsideToggle: boolean
  nativeMappedPos: number | null
  pmFrom: number
}): boolean {
  if (!params.pmInsideToggle) return false
  return params.nativeMappedPos !== params.pmFrom
}
