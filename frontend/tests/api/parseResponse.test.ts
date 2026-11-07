import { describe, expect, it } from 'vitest'

import { ApiConflictError } from '@/api/apiConflict'
import { parseJsonOrThrowApi } from '@/api/parseResponse'

describe('parseJsonOrThrowApi', () => {
  it('при 409 code=conflict бросает ApiConflictError с message из тела', async () => {
    const body = JSON.stringify({
      code: 'conflict',
      message: 'Документ изменён другим пользователем',
    })
    await expect(parseJsonOrThrowApi(new Response(body, { status: 409 }))).rejects.toBeInstanceOf(
      ApiConflictError,
    )
    await expect(parseJsonOrThrowApi(new Response(body, { status: 409 }))).rejects.toThrow(
      'Документ изменён другим пользователем',
    )
  })

  it('при !ok без conflict-code бросает Error с message из тела API', async () => {
    const body = JSON.stringify({ code: 'bad_request', message: 'Некорректный запрос' })
    await expect(parseJsonOrThrowApi(new Response(body, { status: 400 }))).rejects.toThrow(
      'Некорректный запрос',
    )
    await expect(
      parseJsonOrThrowApi(new Response(body, { status: 400 })),
    ).rejects.not.toBeInstanceOf(ApiConflictError)
  })

  it('при 401 без message — формулировка про сессию', async () => {
    const res = new Response('{}', { status: 401 })

    await expect(parseJsonOrThrowApi(res)).rejects.toThrow('Сессия истекла')
  })

  it('успех с телом — распарсенный объект', async () => {
    const res = new Response(JSON.stringify({ id: 'x1', title: 'Doc' }), { status: 200 })

    await expect(parseJsonOrThrowApi<{ id: string; title: string }>(res)).resolves.toEqual({
      id: 'x1',
      title: 'Doc',
    })
  })

  it('успех с пустым телом — undefined (204)', async () => {
    const res = new Response(null, { status: 204 })

    await expect(parseJsonOrThrowApi(res)).resolves.toBeUndefined()
  })
})
