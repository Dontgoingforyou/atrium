import { describe, expect, it } from 'vitest'

import type { AuthUser } from '@/types/auth'
import type { PortalUser } from '@/types/user'
import { getUserDisplayLabel } from '@/utils/userLabel'
import {
  portalUserFromAuthUser,
  withSessionUserInDirectory,
} from '@/utils/user/sessionUserInDirectory'

const session: AuthUser = {
  sub: '3d2fc355-0a8b-4438-b3a3-f6e0ade53433',
  email: 'ivan@example.com',
  username: 'ivan',
  full_name: 'Иван Петров',
  idp_groups: [],
  is_portal_admin: false,
}

const namelessInDirectory: PortalUser = {
  sub: session.sub,
  display_name: null,
  email: null,
  username: null,
}

describe('portalUserFromAuthUser', () => {
  it('кладёт full_name в display_name', () => {
    const u = portalUserFromAuthUser(session)
    expect(u.display_name).toBe('Иван Петров')
    expect(getUserDisplayLabel(u)).toBe('Иван Петров')
  })
})

describe('withSessionUserInDirectory', () => {
  it('без сессии — как пришло (в т.ч. пустой справочник)', () => {
    expect(withSessionUserInDirectory(undefined, null)).toEqual([])
    expect(withSessionUserInDirectory([namelessInDirectory], null)).toEqual([namelessInDirectory])
  })

  it('пустой справочник — всё равно добавляет текущего, чтобы пикер не показывал UUID', () => {
    const merged = withSessionUserInDirectory(undefined, session)
    expect(merged).toHaveLength(1)
    expect(getUserDisplayLabel(merged[0])).toBe('Иван Петров')
  })

  it('если текущего нет в /portal/users — вставляет его в начало', () => {
    const other: PortalUser = {
      sub: 'other',
      display_name: 'Коллега',
      email: null,
      username: null,
    }
    const merged = withSessionUserInDirectory([other], session)
    expect(merged.map((u) => u.sub)).toEqual([session.sub, 'other'])
    expect(getUserDisplayLabel(merged[0])).toBe('Иван Петров')
  })

  it('если в справочнике пустые имена — дополняет из сессии', () => {
    const merged = withSessionUserInDirectory([namelessInDirectory], session)
    expect(merged).toHaveLength(1)
    expect(getUserDisplayLabel(merged[0])).toBe('Иван Петров')
    expect(merged[0].email).toBe('ivan@example.com')
  })

  it('не затирает уже заполненные поля справочника', () => {
    const existing: PortalUser = {
      sub: session.sub,
      display_name: 'Имя из профиля',
      email: 'profile@example.com',
      username: 'profile',
      avatar_url: 'https://cdn.example/a.png',
    }
    const merged = withSessionUserInDirectory([existing], session)
    expect(merged[0].display_name).toBe('Имя из профиля')
    expect(merged[0].email).toBe('profile@example.com')
    expect(merged[0].avatar_url).toBe('https://cdn.example/a.png')
  })
})
