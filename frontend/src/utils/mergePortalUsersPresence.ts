import type { PortalUserPresenceRow, PortalUserShort, UserPresence } from '../api/usersApi'

function effectivePresence(u: PortalUserShort): UserPresence {
  return u.presence ?? 'offline'
}

export function mergePortalUsersPresence(
  users: PortalUserShort[] | undefined,
  rows: PortalUserPresenceRow[],
): PortalUserShort[] | undefined {
  if (!users?.length) {
    return users
  }
  const map = new Map(rows.map((r) => [r.sub, r]))
  let changed = false
  const out = users.map((u) => {
    const row = map.get(u.sub)
    if (row === undefined) {
      return u
    }
    const presenceChanged = row.presence !== effectivePresence(u)
    // last_seen_at: не затираем БД-значение явным null из Redis (только непустая строка)
    const newLastSeen =
      typeof row.last_seen_at === 'string' && row.last_seen_at.length > 0
        ? row.last_seen_at
        : undefined
    const lastSeenChanged = newLastSeen !== undefined && newLastSeen !== u.last_seen_at
    if (!presenceChanged && !lastSeenChanged) {
      return u
    }
    changed = true
    return {
      ...u,
      presence: row.presence,
      ...(newLastSeen !== undefined ? { last_seen_at: newLastSeen } : {}),
    }
  })
  return changed ? out : users
}
