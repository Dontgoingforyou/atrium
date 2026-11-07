import { parseJsonOrThrowApi } from '../parseResponse'
import { authenticatedFetch } from '../rawClient'

export async function fetchPushVapidPublicKey(): Promise<string | null> {
  const res = await authenticatedFetch('/portal/push/vapid-public-key')
  if (res.status === 404) {
    return null
  }
  const data = await parseJsonOrThrowApi<{ public_key: string }>(res)
  return data.public_key?.trim() || null
}

export async function postPushSubscribe(subscription: PushSubscriptionJSON): Promise<void> {
  const res = await authenticatedFetch('/portal/push/subscribe', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(subscription),
  })
  await parseJsonOrThrowApi<void>(res)
}

export async function postPushUnsubscribe(endpoint: string): Promise<void> {
  const res = await authenticatedFetch('/portal/push/unsubscribe', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ endpoint }),
  })
  await parseJsonOrThrowApi<void>(res)
}
