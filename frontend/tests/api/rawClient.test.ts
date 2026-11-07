/**
 * Контракты silentRefreshAccessToken и authenticatedFetch (rawClient.ts).
 *
 * Среда: node. vi.doMock + динамический import — свежий модуль
 * (_refreshPromise = null) и независимый мок authStore.
 *
 * refresh в httpOnly cookie; silentRefresh смотрит expiresAt / user, не refresh из стора.
 */
import { afterEach, describe, expect, it, vi } from 'vitest'

let mockClearSession: ReturnType<typeof vi.fn>
let mockSetSession: ReturnType<typeof vi.fn>
let storeSnapshot: {
  accessToken: string | null
  expiresAt: number | null
  oauthClientId: string | null
  user: object | null
}

afterEach(() => {
  vi.resetModules()
  vi.clearAllMocks()
  vi.unstubAllGlobals()
})

type StoreOpts = {
  expiresAt: number | null
  oauthClientId?: string | null
  /** Явный null — сессия без user (ветка clear после успешного refresh). */
  user?: object | null
  accessToken?: string | null
}

async function setupRawClient(storeState: StoreOpts) {
  mockClearSession = vi.fn()
  mockSetSession = vi.fn((payload: {
    access_token: string
    expires_in: number
    oauth_client_id?: string | null
    user: object
  }) => {
    storeSnapshot.accessToken = payload.access_token
    storeSnapshot.user = payload.user
  })

  storeSnapshot = {
    accessToken: storeState.accessToken ?? 'old-access',
    expiresAt: storeState.expiresAt,
    oauthClientId: storeState.oauthClientId ?? null,
    user: storeState.user !== undefined ? storeState.user : { sub: 'u1' },
  }

  vi.doMock('@/store/authStore', () => ({
    useAuthStore: {
      getState: () => ({
        accessToken: storeSnapshot.accessToken,
        expiresAt: storeSnapshot.expiresAt,
        oauthClientId: storeSnapshot.oauthClientId,
        user: storeSnapshot.user,
        clearSession: mockClearSession,
        setSession: mockSetSession,
      }),
    },
  }))

  return import('@/api/rawClient')
}

describe('silentRefreshAccessToken', () => {
  it('вызывает clearSession и возвращает null, если expiresAt равен null', async () => {
    const { silentRefreshAccessToken } = await setupRawClient({ expiresAt: null })

    const result = await silentRefreshAccessToken()

    expect(result).toBeNull()
    expect(mockClearSession).toHaveBeenCalledOnce()
    expect(mockSetSession).not.toHaveBeenCalled()
  })

  it('делает POST /auth/refresh и вызывает setSession при успехе', async () => {
    const { silentRefreshAccessToken } = await setupRawClient({
      expiresAt: Date.now() + 3600 * 1000,
      oauthClientId: 'my-client',
    })

    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          access_token: 'new-access',
          refresh_token: 'new-refresh',
          expires_in: 1800,
          oauth_client_id: 'my-client',
        }),
      }),
    )

    const result = await silentRefreshAccessToken()

    expect(result).toBe('new-access')
    expect(mockClearSession).not.toHaveBeenCalled()
    expect(mockSetSession).toHaveBeenCalledOnce()

    const called = mockSetSession.mock.calls[0][0] as Record<string, unknown>
    expect(called.access_token).toBe('new-access')
    expect(called.expires_in).toBe(1800)
  })

  it('после успешного refresh без user в сторе — clearSession и null', async () => {
    const { silentRefreshAccessToken } = await setupRawClient({
      expiresAt: Date.now() + 3600 * 1000,
      user: null,
    })

    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          access_token: 'new-access',
          expires_in: 1800,
          oauth_client_id: 'c1',
        }),
      }),
    )

    const result = await silentRefreshAccessToken()

    expect(result).toBeNull()
    expect(mockClearSession).toHaveBeenCalledOnce()
    expect(mockSetSession).not.toHaveBeenCalled()
  })

  it('вызывает clearSession и возвращает null, если /auth/refresh вернул не-200', async () => {
    const { silentRefreshAccessToken } = await setupRawClient({
      expiresAt: Date.now() + 3600 * 1000,
    })

    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValueOnce({ ok: false, status: 401 }),
    )

    const result = await silentRefreshAccessToken()

    expect(result).toBeNull()
    expect(mockClearSession).toHaveBeenCalledOnce()
    expect(mockSetSession).not.toHaveBeenCalled()
  })

  it('при сетевой ошибке НЕ вызывает clearSession и возвращает null', async () => {
    const { silentRefreshAccessToken } = await setupRawClient({
      expiresAt: Date.now() + 3600 * 1000,
    })

    vi.stubGlobal(
      'fetch',
      vi.fn().mockRejectedValueOnce(new Error('Network error')),
    )

    const result = await silentRefreshAccessToken()

    expect(result).toBeNull()
    expect(mockClearSession).not.toHaveBeenCalled()
  })

  it('при null refresh_token в ответе setSession вызывается с корректным access_token', async () => {
    const { silentRefreshAccessToken } = await setupRawClient({
      expiresAt: Date.now() + 3600 * 1000,
      oauthClientId: 'c1',
    })

    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          access_token: 'new-access',
          refresh_token: null,
          expires_in: 900,
          oauth_client_id: 'c1',
        }),
      }),
    )

    const result = await silentRefreshAccessToken()

    expect(result).toBe('new-access')
    expect(mockSetSession).toHaveBeenCalledOnce()
    const called = mockSetSession.mock.calls[0][0] as Record<string, unknown>
    expect(called.access_token).toBe('new-access')
    expect(called.expires_in).toBe(900)
  })

  it('параллельные вызовы дедуплицируют один fetch к /auth/refresh', async () => {
    const { silentRefreshAccessToken } = await setupRawClient({
      expiresAt: Date.now() + 3600 * 1000,
    })

    let resolveRefresh!: (v: unknown) => void
    const refreshBody = new Promise((resolve) => {
      resolveRefresh = resolve
    })

    const fetchMock = vi.fn().mockReturnValueOnce(refreshBody)
    vi.stubGlobal('fetch', fetchMock)

    const p1 = silentRefreshAccessToken()
    const p2 = silentRefreshAccessToken()

    resolveRefresh({
      ok: true,
      json: async () => ({
        access_token: 'deduped',
        expires_in: 600,
        oauth_client_id: 'c1',
      }),
    })

    await expect(Promise.all([p1, p2])).resolves.toEqual(['deduped', 'deduped'])
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })
})

describe('authenticatedFetch', () => {
  it('ставит Authorization Bearer из стора при успешном ответе', async () => {
    const { authenticatedFetch } = await setupRawClient({
      expiresAt: Date.now() + 3600 * 1000,
      accessToken: 'tok-1',
    })

    const fetchMock = vi.fn().mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({}),
    })
    vi.stubGlobal('fetch', fetchMock)

    const res = await authenticatedFetch('/portal/home')

    expect(res.status).toBe(200)
    expect(fetchMock).toHaveBeenCalledTimes(1)
    const init = fetchMock.mock.calls[0][1] as RequestInit
    const headers = new Headers(init.headers)
    expect(headers.get('Authorization')).toBe('Bearer tok-1')
  })

  it('при 401 и успешном refresh повторяет запрос с новым Bearer', async () => {
    const { authenticatedFetch } = await setupRawClient({
      expiresAt: Date.now() + 3600 * 1000,
      accessToken: 'old-tok',
      oauthClientId: 'cli',
    })

    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({ ok: false, status: 401 })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          access_token: 'fresh-tok',
          expires_in: 1200,
          oauth_client_id: 'cli',
        }),
      })
      .mockResolvedValueOnce({ ok: true, status: 200 })
    vi.stubGlobal('fetch', fetchMock)

    const res = await authenticatedFetch('/portal/account')

    expect(res.status).toBe(200)
    expect(fetchMock).toHaveBeenCalledTimes(3)
    const retryInit = fetchMock.mock.calls[2][1] as RequestInit
    expect(new Headers(retryInit.headers).get('Authorization')).toBe('Bearer fresh-tok')
  })

  it('при 401 и неудачном refresh возвращает исходный 401', async () => {
    const { authenticatedFetch } = await setupRawClient({
      expiresAt: Date.now() + 3600 * 1000,
      accessToken: 'old-tok',
    })

    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({ ok: false, status: 401 })
      .mockResolvedValueOnce({ ok: false, status: 401 })
    vi.stubGlobal('fetch', fetchMock)

    const res = await authenticatedFetch('/portal/account')

    expect(res.status).toBe(401)
    expect(fetchMock).toHaveBeenCalledTimes(2)
    expect(mockClearSession).toHaveBeenCalled()
  })
})
