/** Локализация Notification.permission для UI. */
export function notificationPermissionLabelRu(perm: NotificationPermission): string {
  switch (perm) {
    case 'granted':
      return 'разрешено'
    case 'denied':
      return 'запрещено'
    default:
      return 'не запрошено'
  }
}
