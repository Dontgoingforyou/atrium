export type ChatsLeftView = 'list' | 'picker' | 'groupPicker'

/** Совпадает с master-detail брейкпоинтом в ChatsPageSidebar/Thread CSS. */
export const CHATS_NARROW_MAX_WIDTH_PX = 900

export function isChatsNarrowViewport(widthPx: number): boolean {
  return widthPx <= CHATS_NARROW_MAX_WIDTH_PX
}

export function shouldClearActiveChatOnBackToList(
  leftView: ChatsLeftView,
  isNarrow: boolean,
): boolean {
  return isNarrow && leftView !== 'list'
}
