import { parseJsonOrThrowApi } from './parseResponse'
import { apiFetch } from './rawClient'

export type HealthResponse = {
  status: string
}

export async function fetchHealth(signal?: AbortSignal): Promise<HealthResponse> {
  const response = await apiFetch('/health', {
    signal,
    headers: { Accept: 'application/json' },
  })
  return parseJsonOrThrowApi<HealthResponse>(response)
}
