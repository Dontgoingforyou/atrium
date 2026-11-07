import { parseJsonOrThrowApi } from './parseResponse'
import { authenticatedFetch } from './rawClient'

export type PortalAccountPreferences = {
  notify_document_trash: boolean
  guided_tour_completed: boolean
}

export const ACCOUNT_PREFERENCES_QUERY_KEY = ['portal', 'account', 'preferences'] as const

export async function getAccountPreferences(): Promise<PortalAccountPreferences> {
  const res = await authenticatedFetch('/portal/account/preferences')
  return parseJsonOrThrowApi<PortalAccountPreferences>(res)
}

export async function patchAccountPreferences(
  body: Partial<PortalAccountPreferences>,
): Promise<PortalAccountPreferences> {
  const res = await authenticatedFetch('/portal/account/preferences', {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return parseJsonOrThrowApi<PortalAccountPreferences>(res)
}
