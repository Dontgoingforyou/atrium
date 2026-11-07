import { describe, expect, it, vi } from 'vitest'

vi.mock('@/api/rawClient', () => ({
  authenticatedFetch: vi.fn(),
}))

import { addFavorite, listFavorites } from '@/api/favorites/favoritesApi'
import { authenticatedFetch } from '@/api/rawClient'

describe('favoritesApi', () => {
  it('listFavorites запрашивает полный набор до потолка API и возвращает массив', async () => {
    const payload = [
      {
        id: 'fav-1',
        target_type: 'document',
        target_id: 'doc-1',
        created_at: '2020-01-01T00:00:00Z',
        title: 'T',
      },
    ]
    vi.mocked(authenticatedFetch).mockResolvedValue(
      new Response(JSON.stringify(payload), { status: 200 }),
    )

    await expect(listFavorites()).resolves.toEqual(payload)
    expect(authenticatedFetch).toHaveBeenCalledWith('/portal/favorites?limit=500')
  })

  it('listFavorites при !ok пробрасывает user-facing ошибку', async () => {
    vi.mocked(authenticatedFetch).mockResolvedValue(
      new Response(JSON.stringify({ code: 'forbidden', message: 'Недостаточно прав' }), {
        status: 403,
      }),
    )

    await expect(listFavorites()).rejects.toThrow('Недостаточно прав')
  })

  it('addFavorite отправляет document в теле', async () => {
    vi.mocked(authenticatedFetch).mockResolvedValue(
      new Response(
        JSON.stringify({
          id: 'fav-id',
          target_type: 'document',
          target_id: 'doc-uuid',
          created_at: '2020-01-01T00:00:00Z',
          title: 'T',
        }),
        { status: 201 },
      ),
    )
    await addFavorite({ target_type: 'document', target_id: 'doc-uuid' })
    expect(authenticatedFetch).toHaveBeenCalledWith(
      '/portal/favorites',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ target_type: 'document', target_id: 'doc-uuid' }),
      }),
    )
  })
})
