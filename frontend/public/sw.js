self.addEventListener('push', (event) => {
  let data = {}
  try {
    data = event.data ? event.data.json() : {}
  } catch {
    /* ignore */
  }
  const title = typeof data.title === 'string' ? data.title : 'Atrium'
  const body = typeof data.body === 'string' ? data.body : 'Новое сообщение'
  const url = typeof data.url === 'string' ? data.url : '/chats'
  const tag = typeof data.tag === 'string' ? data.tag : 'portal-chat'
  event.waitUntil(
    self.registration.showNotification(title, {
      body,
      tag,
      data: { url },
      icon: '/favicon-192x192.png',
    }),
  )
})

self.addEventListener('notificationclick', (event) => {
  event.notification.close()
  const url = event.notification?.data?.url || '/chats'
  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
      for (const c of clientList) {
        if (c.url && 'focus' in c) {
          void c.focus()
          if ('navigate' in c && typeof c.navigate === 'function') {
            try {
              c.navigate(url)
            } catch {
              void self.clients.openWindow(url)
            }
          } else {
            void self.clients.openWindow(url)
          }
          return
        }
      }
      if (self.clients.openWindow) {
        return self.clients.openWindow(url)
      }
      return undefined
    }),
  )
})
