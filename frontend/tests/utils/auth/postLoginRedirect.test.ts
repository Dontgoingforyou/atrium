// @vitest-environment jsdom

import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/constants/docsAuth', () => ({
  stashDocsBearerToken: vi.fn(),
}))

import { stashDocsBearerToken } from '@/constants/docsAuth'
import { goToPostLoginPath, isAdminPanelPath, isDocsOrRedocPath } from '@/utils/auth/postLoginRedirect'

describe('isAdminPanelPath / isDocsOrRedocPath', () => {
  it('распознаёт SQLAdmin, но не admin-bridge', () => {
    expect(isAdminPanelPath('/admin')).toBe(true)
    expect(isAdminPanelPath('/admin/')).toBe(true)
    expect(isAdminPanelPath('/admin/portal_task/list')).toBe(true)
    expect(isAdminPanelPath('/admin-bridge')).toBe(false)
  })

  it('распознаёт docs/redoc', () => {
    expect(isDocsOrRedocPath('/docs')).toBe(true)
    expect(isDocsOrRedocPath('/docs#/')).toBe(true)
    expect(isDocsOrRedocPath('/docs/oauth2')).toBe(true)
    expect(isDocsOrRedocPath('/redoc')).toBe(true)
    expect(isDocsOrRedocPath('/tasks')).toBe(false)
    expect(isDocsOrRedocPath('/docsfoo')).toBe(false)
    expect(isDocsOrRedocPath('/redocs')).toBe(false)
  })
})

describe('goToPostLoginPath', () => {
  const navigate = vi.fn()
  let assignedHref: string | undefined

  beforeEach(() => {
    navigate.mockReset()
    vi.mocked(stashDocsBearerToken).mockReset()
    assignedHref = undefined
    Object.defineProperty(window, 'location', {
      configurable: true,
      value: {
        origin: 'https://portal.test',
        set href(v: string) {
          assignedHref = v
        },
        get href() {
          return assignedHref ?? 'https://portal.test/'
        },
      },
    })
  })

  it('admin → /admin-bridge без stash и без полной перезагрузки', () => {
    goToPostLoginPath('/admin/', 'tok', navigate)
    expect(navigate).toHaveBeenCalledWith('/admin-bridge', { replace: true })
    expect(stashDocsBearerToken).not.toHaveBeenCalled()
    expect(assignedHref).toBeUndefined()
  })

  it('docs → location.href + stash', () => {
    goToPostLoginPath('/docs', 'tok', navigate)
    expect(navigate).not.toHaveBeenCalled()
    expect(stashDocsBearerToken).toHaveBeenCalledWith('tok')
    expect(assignedHref).toBe('/docs')
  })

  it('SPA-путь → navigate', () => {
    goToPostLoginPath('/tasks', 'tok', navigate)
    expect(navigate).toHaveBeenCalledWith('/tasks', { replace: true })
    expect(stashDocsBearerToken).not.toHaveBeenCalled()
  })

  it('evil URL → navigate на / без stash и без location.href', () => {
    goToPostLoginPath('https://evil.example/x', 'tok', navigate)
    expect(navigate).toHaveBeenCalledWith('/', { replace: true })
    expect(stashDocsBearerToken).not.toHaveBeenCalled()
    expect(assignedHref).toBeUndefined()

    navigate.mockReset()
    goToPostLoginPath('//evil.example/phish', 'tok', navigate)
    expect(navigate).toHaveBeenCalledWith('/', { replace: true })

    navigate.mockReset()
    goToPostLoginPath('javascript:alert(1)', 'tok', navigate)
    expect(navigate).toHaveBeenCalledWith('/', { replace: true })
  })
})
