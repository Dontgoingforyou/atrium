export function chatsPageHref(chatId?: string | null, messageId?: string | null): string {
  if (!chatId) return '/chats'
  const params: Record<string, string> = { chat: chatId }
  if (messageId) params.message = messageId
  return `/chats?${new URLSearchParams(params).toString()}`
}
