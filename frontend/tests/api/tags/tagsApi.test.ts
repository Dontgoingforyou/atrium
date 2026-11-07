import { describe, expect, it, vi } from 'vitest'

vi.mock('@/api/rawClient', () => ({
  authenticatedFetch: vi.fn(),
}))

import { deleteTag } from '@/api/tags/tagsApi'
import { authenticatedFetch } from '@/api/rawClient'

describe('tagsApi', () => {
  it('deleteTag при 204 завершается без ошибки', async () => {
    vi.mocked(authenticatedFetch).mockResolvedValue(new Response(null, { status: 204 }))

    await expect(deleteTag('tag-id')).resolves.toBeUndefined()
    expect(authenticatedFetch).toHaveBeenCalledWith('/portal/tags/tag-id', { method: 'DELETE' })
  })

  it('deleteTag бросает ошибку при 409', async () => {
    vi.mocked(authenticatedFetch).mockResolvedValue(
      new Response(
        JSON.stringify({ code: 'conflict', message: 'Тег используется и не может быть удалён' }),
        { status: 409 },
      ),
    )
    await expect(deleteTag('tag-id')).rejects.toThrow('Тег используется')
  })
})
