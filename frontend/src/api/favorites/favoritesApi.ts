import type { FavoriteCreate, PortalFavorite } from '../../types/favorite'
import { parseJsonOrThrowApi } from '../parseResponse'
import { authenticatedFetch } from '../rawClient'

/** Потолок API (`le=500`): звезда на карточке ищет id во всём ответе, без постраничного UI. */
const FAVORITES_LIST_LIMIT = 500

export async function listFavorites(): Promise<PortalFavorite[]> {
  const qs = new URLSearchParams({ limit: String(FAVORITES_LIST_LIMIT) })
  const res = await authenticatedFetch(`/portal/favorites?${qs}`)
  return parseJsonOrThrowApi(res)
}

export async function addFavorite(body: FavoriteCreate): Promise<PortalFavorite> {
  const res = await authenticatedFetch('/portal/favorites', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return parseJsonOrThrowApi(res)
}

export async function removeFavorite(favoriteId: string): Promise<void> {
  const res = await authenticatedFetch(`/portal/favorites/${favoriteId}`, {
    method: 'DELETE',
  })
  return parseJsonOrThrowApi(res)
}
