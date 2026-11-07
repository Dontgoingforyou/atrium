import { describe, expect, it } from 'vitest'

import type { PortalUserPresenceRow, PortalUserShort } from '../../src/api/usersApi'
import { mergePortalUsersPresence } from '../../src/utils/mergePortalUsersPresence'

describe('mergePortalUsersPresence', () => {
  it('обновляет только presence, avatar_url сохраняется', () => {
    const users: PortalUserShort[] = [
      {
        sub: 'a',
        display_name: 'A',
        email: null,
        username: null,
        presence: 'offline',
        avatar_url: 'https://example.com/a.jpg',
      },
      {
        sub: 'b',
        display_name: 'B',
        email: null,
        username: null,
        presence: 'offline',
        avatar_url: undefined,
      },
    ]
    const rows: PortalUserPresenceRow[] = [
      { sub: 'a', presence: 'online' },
      { sub: 'b', presence: 'away' },
    ]
    const merged = mergePortalUsersPresence(users, rows)
    expect(merged?.[0].presence).toBe('online')
    expect(merged?.[0].avatar_url).toBe('https://example.com/a.jpg')
    expect(merged?.[1].presence).toBe('away')
  })

  it('при undefined кэша возвращает undefined', () => {
    expect(mergePortalUsersPresence(undefined, [])).toBeUndefined()
  })

  it('при пустом кэше возвращает пустой массив', () => {
    expect(mergePortalUsersPresence([], [{ sub: 'x', presence: 'online' }])).toEqual([])
  })

  it('не меняет ссылки на пользователей, если presence совпадает', () => {
    const users: PortalUserShort[] = [
      {
        sub: 'a',
        display_name: 'A',
        email: null,
        username: null,
        presence: 'offline',
        avatar_url: 'https://example.com/a.jpg',
      },
    ]
    const rows: PortalUserPresenceRow[] = [{ sub: 'a', presence: 'offline' }]
    const merged = mergePortalUsersPresence(users, rows)
    expect(merged).toBe(users)
    expect(merged?.[0]).toBe(users[0])
  })

  it('сопоставляет отсутствие presence с offline', () => {
    const users: PortalUserShort[] = [
      {
        sub: 'a',
        display_name: 'A',
        email: null,
        username: null,
        avatar_url: undefined,
      },
    ]
    const rows: PortalUserPresenceRow[] = [{ sub: 'a', presence: 'offline' }]
    expect(mergePortalUsersPresence(users, rows)).toBe(users)
  })

  it('обновляет last_seen_at вместе с presence', () => {
    const users: PortalUserShort[] = [
      {
        sub: 'a',
        display_name: 'A',
        email: null,
        username: null,
        presence: 'online',
        last_seen_at: '2026-05-01T10:00:00+00:00',
      },
    ]
    const rows: PortalUserPresenceRow[] = [
      { sub: 'a', presence: 'offline', last_seen_at: '2026-05-15T12:00:00+00:00' },
    ]
    const merged = mergePortalUsersPresence(users, rows)
    expect(merged?.[0].presence).toBe('offline')
    expect(merged?.[0].last_seen_at).toBe('2026-05-15T12:00:00+00:00')
  })

  it('не затирает last_seen_at при null из presence (Redis без ключа)', () => {
    const users: PortalUserShort[] = [
      {
        sub: 'a',
        display_name: 'A',
        email: null,
        username: null,
        presence: 'offline',
        last_seen_at: '2026-05-01T10:00:00+00:00',
      },
    ]
    const rows: PortalUserPresenceRow[] = [{ sub: 'a', presence: 'offline', last_seen_at: null }]
    const merged = mergePortalUsersPresence(users, rows)
    expect(merged?.[0].presence).toBe('offline')
    expect(merged?.[0].last_seen_at).toBe('2026-05-01T10:00:00+00:00')
  })

  it('не меняет last_seen_at если в строке он undefined', () => {
    const users: PortalUserShort[] = [
      {
        sub: 'a',
        display_name: 'A',
        email: null,
        username: null,
        presence: 'online',
        last_seen_at: '2026-05-01T10:00:00+00:00',
      },
    ]
    // row без last_seen_at (старый формат)
    const rows: PortalUserPresenceRow[] = [{ sub: 'a', presence: 'offline' }]
    const merged = mergePortalUsersPresence(users, rows)
    expect(merged?.[0].presence).toBe('offline')
    expect(merged?.[0].last_seen_at).toBe('2026-05-01T10:00:00+00:00')
  })

  it('не меняет ссылку если presence и last_seen_at не изменились', () => {
    const users: PortalUserShort[] = [
      {
        sub: 'a',
        display_name: 'A',
        email: null,
        username: null,
        presence: 'offline',
        last_seen_at: '2026-05-15T12:00:00+00:00',
      },
    ]
    const rows: PortalUserPresenceRow[] = [
      { sub: 'a', presence: 'offline', last_seen_at: '2026-05-15T12:00:00+00:00' },
    ]
    const merged = mergePortalUsersPresence(users, rows)
    expect(merged).toBe(users)
    expect(merged?.[0]).toBe(users[0])
  })
})
