/** Префиксы и разбор id для DnD деревьев документов в сайдбаре. */

export const DOC_DND_PREFIX = 'doc:'
export const SECTION_DND_PREFIX = 'section:'

export function docDndId(documentId: string): string {
  return `${DOC_DND_PREFIX}${documentId}`
}

export function sectionDndId(slug: string): string {
  return `${SECTION_DND_PREFIX}${slug}`
}

export function parseDocDndId(dndId: string | number): string | null {
  const s = String(dndId)
  return s.startsWith(DOC_DND_PREFIX) ? s.slice(DOC_DND_PREFIX.length) : null
}

export function parseSectionDndSlug(dndId: string | number): string | null {
  const s = String(dndId)
  return s.startsWith(SECTION_DND_PREFIX) ? s.slice(SECTION_DND_PREFIX.length) : null
}
