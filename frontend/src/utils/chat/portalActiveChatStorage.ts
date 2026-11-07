import {
  PORTAL_ACTIVE_CHAT_CHATS_PAGE_KEY,
  PORTAL_ACTIVE_CHAT_FLOATING_WIDGET_KEY,
} from '../../constants/portalActiveChat'

export function setPortalActiveChatOnChatsPage(chatId: string | null): void {
  try {
    if (chatId) {
      sessionStorage.setItem(PORTAL_ACTIVE_CHAT_CHATS_PAGE_KEY, chatId)
    } else {
      sessionStorage.removeItem(PORTAL_ACTIVE_CHAT_CHATS_PAGE_KEY)
    }
  } catch {
    /* sessionStorage недоступен */
  }
}

export function setPortalActiveChatOnFloatingWidget(chatId: string | null): void {
  try {
    if (chatId) {
      sessionStorage.setItem(PORTAL_ACTIVE_CHAT_FLOATING_WIDGET_KEY, chatId)
    } else {
      sessionStorage.removeItem(PORTAL_ACTIVE_CHAT_FLOATING_WIDGET_KEY)
    }
  } catch {
    /* ignore */
  }
}

export function readPortalFocusedChatIds(): { chatsPage: string | null; widget: string | null } {
  try {
    return {
      chatsPage: sessionStorage.getItem(PORTAL_ACTIVE_CHAT_CHATS_PAGE_KEY),
      widget: sessionStorage.getItem(PORTAL_ACTIVE_CHAT_FLOATING_WIDGET_KEY),
    }
  } catch {
    return { chatsPage: null, widget: null }
  }
}
