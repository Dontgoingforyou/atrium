export function portalChatMessagesPageQueryKey(
  chatId: string,
  mode: 'wide' | 'default',
) {
  return ['portal', 'messages', chatId, mode] as const
}

export type PortalChatMessagesPageQueryKey = ReturnType<typeof portalChatMessagesPageQueryKey>
export type BuildPortalMessagesPageQueryKey = (chatId: string) => PortalChatMessagesPageQueryKey

export const PORTAL_MESSAGES_IDLE_QUERY_KEY = [
  'portal',
  'messages',
  '__idle__',
  'default',
] as const
