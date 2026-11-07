import { authenticatedFetch } from '../../api/rawClient'

export async function fetchWsTicket(path: string): Promise<string | null> {
  const res = await authenticatedFetch(path, { method: 'POST' })
  if (!res.ok) return null
  const data = (await res.json()) as { ticket?: unknown }
  return typeof data.ticket === 'string' ? data.ticket : null
}
