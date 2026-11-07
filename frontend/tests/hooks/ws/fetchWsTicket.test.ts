import { beforeEach, describe, expect, it, vi } from 'vitest'

const authenticatedFetch = vi.fn()

vi.mock('@/api/rawClient', () => ({
  authenticatedFetch: (...args: unknown[]) => authenticatedFetch(...args),
}))

describe('fetchWsTicket', () => {
  beforeEach(() => {
    authenticatedFetch.mockReset()
  })

  it('ok + ticket string → ticket', async () => {
    authenticatedFetch.mockResolvedValue(
      new Response(JSON.stringify({ ticket: 't-1' }), { status: 200 }),
    )
    const { fetchWsTicket } = await import('@/hooks/ws/fetchWsTicket')
    await expect(fetchWsTicket('/api/v1/portal/inbox/ws-ticket')).resolves.toBe('t-1')
    expect(authenticatedFetch).toHaveBeenCalledWith('/api/v1/portal/inbox/ws-ticket', {
      method: 'POST',
    })
  })

  it('!ok → null (не бросает)', async () => {
    authenticatedFetch.mockResolvedValue(new Response('nope', { status: 401 }))
    const { fetchWsTicket } = await import('@/hooks/ws/fetchWsTicket')
    await expect(fetchWsTicket('/ticket')).resolves.toBeNull()
  })

  it('ok без string ticket → null', async () => {
    authenticatedFetch.mockResolvedValue(
      new Response(JSON.stringify({ ticket: 123 }), { status: 200 }),
    )
    const { fetchWsTicket } = await import('@/hooks/ws/fetchWsTicket')
    await expect(fetchWsTicket('/ticket')).resolves.toBeNull()
  })

  it('ok без поля ticket → null', async () => {
    authenticatedFetch.mockResolvedValue(new Response(JSON.stringify({}), { status: 200 }))
    const { fetchWsTicket } = await import('@/hooks/ws/fetchWsTicket')
    await expect(fetchWsTicket('/ticket')).resolves.toBeNull()
  })
})
