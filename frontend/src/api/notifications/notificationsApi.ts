import type { NotificationUnreadCount, PortalNotification } from '../../types/notification'
import { parseJsonOrThrowApi } from '../parseResponse'
import { authenticatedFetch } from '../rawClient'

export async function listNotifications(params?: {
  unread_only?: boolean
  skip?: number
  limit?: number
}): Promise<PortalNotification[]> {
  const qs = new URLSearchParams()
  if (params?.unread_only !== undefined) qs.set('unread_only', String(params.unread_only))
  if (params?.skip !== undefined) qs.set('skip', String(params.skip))
  if (params?.limit !== undefined) qs.set('limit', String(params.limit))
  const query = qs.toString() ? `?${qs}` : ''
  const res = await authenticatedFetch(`/portal/notifications${query}`)
  return parseJsonOrThrowApi(res)
}

export async function getUnreadCount(): Promise<NotificationUnreadCount> {
  const res = await authenticatedFetch('/portal/notifications/unread-count')
  return parseJsonOrThrowApi(res)
}

export async function markNotificationRead(notificationId: string): Promise<PortalNotification> {
  const res = await authenticatedFetch(`/portal/notifications/${notificationId}/read`, {
    method: 'POST',
  })
  return parseJsonOrThrowApi(res)
}

export async function markAllNotificationsRead(): Promise<NotificationUnreadCount> {
  const res = await authenticatedFetch('/portal/notifications/mark-all-read', {
    method: 'POST',
  })
  return parseJsonOrThrowApi(res)
}

export async function deleteNotification(notificationId: string): Promise<void> {
  const res = await authenticatedFetch(`/portal/notifications/${notificationId}`, {
    method: 'DELETE',
  })
  await parseJsonOrThrowApi(res)
}

export async function deleteAllNotifications(): Promise<void> {
  const res = await authenticatedFetch('/portal/notifications', { method: 'DELETE' })
  await parseJsonOrThrowApi(res)
}
