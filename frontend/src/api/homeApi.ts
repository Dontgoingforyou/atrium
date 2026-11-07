import type { HomeData } from '../types/home'
import { parseJsonOrThrowApi } from './parseResponse'
import { authenticatedFetch } from './rawClient'

export async function fetchHome(assigneeSub?: string | null): Promise<HomeData> {
  const qs = assigneeSub ? `?assignee_sub=${encodeURIComponent(assigneeSub)}` : ''
  const res = await authenticatedFetch(`/portal/home${qs}`)
  return parseJsonOrThrowApi(res)
}
