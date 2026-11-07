/** Декодирование base64url к Uint8Array для `applicationServerKey` (Web Push). */
export function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4)
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/')
  const rawData = window.atob(base64)
  const outputArray = new Uint8Array(rawData.length)
  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i)
  }
  return outputArray
}

export async function ensureServiceWorkerRegistered(): Promise<ServiceWorkerRegistration> {
  if (!('serviceWorker' in navigator)) {
    throw new Error('service_worker_unsupported')
  }
  return navigator.serviceWorker.register('/sw.js', { scope: '/' })
}

export async function subscribeCurrentUserToWebPush(publicKeyB64: string): Promise<PushSubscriptionJSON> {
  const reg = await navigator.serviceWorker.ready
  /** Копия с «обычным» ArrayBuffer — совместимо с типом `BufferSource` в lib.dom при `tsc -b`. */
  const applicationServerKey = Uint8Array.from(urlBase64ToUint8Array(publicKeyB64))
  const sub = await reg.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey,
  })
  const json = sub.toJSON()
  if (!json.endpoint || !json.keys?.p256dh || !json.keys?.auth) {
    throw new Error('push_subscription_incomplete')
  }
  return json
}
