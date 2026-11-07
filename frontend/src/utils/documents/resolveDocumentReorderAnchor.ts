export type DocumentReorderAnchor =
  | { before_id: string; after_id?: undefined }
  | { after_id: string; before_id?: undefined }


export function resolveDocumentReorderAnchor(
  ordered: ReadonlyArray<{ id: string }>,
  movedId: string,
): DocumentReorderAnchor | null {
  const newIdx = ordered.findIndex((d) => d.id === movedId)
  if (newIdx < 0 || ordered.length < 2) return null
  if (newIdx < ordered.length - 1) {
    return { before_id: ordered[newIdx + 1]!.id }
  }
  return { after_id: ordered[newIdx - 1]!.id }
}
