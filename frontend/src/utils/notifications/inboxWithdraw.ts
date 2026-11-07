export const PORTAL_NOTIFICATION_UPDATE_EVENT = 'portal_notification_update'
export const PORTAL_NOTIFICATION_WITHDRAWN_EVENT = 'portal_notification_withdrawn'
export const DM_INBOX_UPDATE_EVENT = 'dm_inbox_update'
export const DM_INBOX_WITHDRAWN_EVENT = 'dm_inbox_withdrawn'

/** Звук колокольчика только у нового уведомления, не у отзыва после удаления. */
export function portalNotificationEventPlaysSound(eventName: string): boolean {
  return eventName === PORTAL_NOTIFICATION_UPDATE_EVENT
}

export function shouldDismissChatInboxToast(
  openChatId: string | null | undefined,
  withdrawnChatId: string,
): boolean {
  return openChatId != null && openChatId === withdrawnChatId
}

export function chatInboxOsNotificationTag(chatId: string): string {
  return `portal-chat-${chatId}`
}

type ClosableNotification = { close: () => void }

const osByTag = new Map<string, ClosableNotification>()

export function trackChatInboxOsNotification(chatId: string, notification: ClosableNotification): void {
  osByTag.set(chatInboxOsNotificationTag(chatId), notification)
}

export function closeTrackedChatInboxOsNotification(chatId: string): void {
  const tag = chatInboxOsNotificationTag(chatId)
  const notification = osByTag.get(tag)
  if (!notification) return
  notification.close()
  osByTag.delete(tag)
}
