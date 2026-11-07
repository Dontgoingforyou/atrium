import type { ThreadComment } from '../../types/commentThread'

function flattenComments(comments: ThreadComment[]): ThreadComment[] {
  return comments.flatMap((c) => [c, ...flattenComments(c.replies)])
}

export function panelContentCountWhenLoaded(
  isSuccess: boolean,
  count: number | undefined,
): number | undefined {
  return isSuccess ? (count ?? 0) : undefined
}

export function countLinksPanelContent(input: {
  hasDocument: boolean
  hasParent: boolean
  subtasksLoaded: boolean
  subtaskCount: number
}): number | undefined {
  const known = (input.hasDocument ? 1 : 0) + (input.hasParent ? 1 : 0)
  if (!input.subtasksLoaded) {
    return known > 0 ? known : undefined
  }
  return known + input.subtaskCount
}

/** Число комментариев с текстом или вложениями — для авто-раскрытия панели. */
export function countCommentsPanelContent(comments: ThreadComment[] | undefined): number {
  if (!comments?.length) return 0
  return flattenComments(comments).filter(
    (c) => c.body.trim().length > 0 || (c.media?.length ?? 0) > 0,
  ).length
}

/**
 * Открытость сворачиваемой секции: пока пользователь не переключил её вручную
 * (`manualOverride === null`) — раскрыта, если есть содержимое; после ручного
 * переключения — выбор пользователя не перекрывается наличием/отсутствием данных.
 */
export function resolveManualOrAutoOpen(manualOverride: boolean | null, hasContent: boolean): boolean {
  return manualOverride ?? hasContent
}
