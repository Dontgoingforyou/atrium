export type PortalFocusedChats = { chatsPage: string | null; widget: string | null }

/**
 * Не показывать тост / дублирующее системное уведомление, если вкладка видима
 * и пользователь уже в этом чате (страница /chats или плавающий виджет).
 */
export function shouldSuppressChatInboxToast(args: {
  eventChatId: string
  pathname: string
  search: string
  visibilityState: DocumentVisibilityState
  focused: PortalFocusedChats
}): boolean {
  if (args.visibilityState !== 'visible') {
    return false
  }
  const { eventChatId, pathname, search, focused } = args
  if (pathname === '/chats' || pathname.startsWith('/chats/')) {
    const params = new URLSearchParams(search.startsWith('?') ? search : `?${search}`)
    const urlChat = params.get('chat')
    if (urlChat === eventChatId) {
      return true
    }
  }
  if (focused.chatsPage === eventChatId || focused.widget === eventChatId) {
    return true
  }
  return false
}

/** Замьюченный чат: тост/OS только при @упоминании. */
export function shouldSuppressDueToMute(chatMuted: boolean, isMentioned: boolean): boolean {
  return chatMuted && !isMentioned
}

export function shouldShowChatInboxToast(args: {
  eventChatId: string
  pathname: string
  search: string
  visibilityState: DocumentVisibilityState
  focused: PortalFocusedChats
  toastEnabled: boolean
  chatMuted: boolean
  isMentioned: boolean
}): boolean {
  if (shouldSuppressChatInboxToast(args)) return false
  if (shouldSuppressDueToMute(args.chatMuted, args.isMentioned)) return false
  return args.toastEnabled
}
