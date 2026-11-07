export function nestedSiblingOrderKey(siblingIds: readonly string[]): string {
  return siblingIds.join(',')
}

type RectLike = { top: number; height: number }

export function resolveNestedInsertIndex(
  orderedIds: readonly string[],
  movedId: string,
  pointerY: number,
  getRect: (id: string) => RectLike | undefined,
): number | null {
  const fromIdx = orderedIds.indexOf(movedId)
  if (fromIdx < 0 || orderedIds.length < 2) return null

  const withoutMoved = orderedIds.filter((id) => id !== movedId)
  let targetInWithout = withoutMoved.length
  for (let i = 0; i < withoutMoved.length; i++) {
    const id = withoutMoved[i]!
    const rect = getRect(id)
    if (!rect || rect.height <= 0) continue
    if (pointerY < rect.top + rect.height / 2) {
      targetInWithout = i
      break
    }
  }

  if (targetInWithout === fromIdx) return null
  return targetInWithout
}
