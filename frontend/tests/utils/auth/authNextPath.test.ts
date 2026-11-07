// @vitest-environment jsdom

import { beforeEach, describe, expect, it } from 'vitest'

import { resolveLoginNextQueryParam, shouldSaveAuthNextPath } from '@/utils/auth/authNextPath'

beforeEach(() => {
  Object.defineProperty(window, 'location', {
    configurable: true,
    value: { origin: 'https://portal.test' },
  })
})

describe('shouldSaveAuthNextPath', () => {
  it('пропускает обычные маршруты портала', () => {
    expect(shouldSaveAuthNextPath('/')).toBe(true)
    expect(shouldSaveAuthNextPath('/chats')).toBe(true)
    expect(shouldSaveAuthNextPath('/tasks/123')).toBe(true)
    expect(shouldSaveAuthNextPath('/p/trash?tab=docs')).toBe(true)
  })

  it('отсекает /login — иначе post-login redirect зациклится', () => {
    expect(shouldSaveAuthNextPath('/login')).toBe(false)
    expect(shouldSaveAuthNextPath('/login?next=/tasks')).toBe(false)
    expect(shouldSaveAuthNextPath('/login#frag')).toBe(false)
  })

  it('отсекает OAuth callback /auth/*', () => {
    expect(shouldSaveAuthNextPath('/auth/callback')).toBe(false)
    expect(shouldSaveAuthNextPath('/auth/callback?code=abc&state=xyz')).toBe(false)
  })

  it('не путает /auth с путями, просто содержащими префикс как сегмент', () => {
    expect(shouldSaveAuthNextPath('/authenticator')).toBe(true)
    expect(shouldSaveAuthNextPath('/authorization')).toBe(true)
  })
})

describe('resolveLoginNextQueryParam', () => {
  it('пустой / отсутствующий next → null (не затирать auth_next из RequireAuth)', () => {
    expect(resolveLoginNextQueryParam(null)).toBeNull()
    expect(resolveLoginNextQueryParam(undefined)).toBeNull()
    expect(resolveLoginNextQueryParam('')).toBeNull()
    expect(resolveLoginNextQueryParam('   ')).toBeNull()
  })

  it('валидный next → санитизированный путь', () => {
    expect(resolveLoginNextQueryParam('/tasks')).toBe('/tasks')
    expect(resolveLoginNextQueryParam('/chats?tab=1')).toBe('/chats?tab=1')
  })

  it('next=/login или /auth/* → null (не цикл post-login)', () => {
    expect(resolveLoginNextQueryParam('/login')).toBeNull()
    expect(resolveLoginNextQueryParam('/login?x=1')).toBeNull()
    expect(resolveLoginNextQueryParam('/auth/callback')).toBeNull()
  })

  it('open redirect через next → безопасный / не пишется как цель цикла', () => {
    expect(resolveLoginNextQueryParam('//evil.example')).toBe('/')
    expect(resolveLoginNextQueryParam('https://evil.example/x')).toBe('/')
    expect(resolveLoginNextQueryParam('javascript:alert(1)')).toBe('/')
  })
})
