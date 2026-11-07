import { describe, expect, it } from 'vitest'

import { createPkcePair } from '@/utils/auth/pkce'

describe('createPkcePair', () => {
  it('возвращает verifier и S256 challenge (base64url)', async () => {
    const { verifier, challenge } = await createPkcePair()
    expect(verifier.length).toBeGreaterThanOrEqual(64)
    expect(challenge).toMatch(/^[A-Za-z0-9_-]+$/)
    expect(challenge.length).toBeGreaterThan(20)
  })
})
