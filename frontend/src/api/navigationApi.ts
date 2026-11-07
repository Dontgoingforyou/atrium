import type { PortalNavNodeTree } from '../types/portalNavigation'
import { parseJsonOrThrowApi } from './parseResponse'
import { authenticatedFetch } from './rawClient'

export async function fetchNavigationTree(): Promise<PortalNavNodeTree[]> {
  const res = await authenticatedFetch('/portal/navigation-tree')
  return parseJsonOrThrowApi(res)
}
