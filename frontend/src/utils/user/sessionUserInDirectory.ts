import type { AuthUser } from '../../types/auth'
import type { PortalUser } from '../../types/user'

/** AuthUser → PortalUser: в сессии имя в `full_name`, в справочнике — `display_name`. */
export function portalUserFromAuthUser(user: AuthUser): PortalUser {
  return {
    sub: user.sub,
    display_name: user.full_name || null,
    email: user.email || null,
    username: user.username || null,
    avatar_url: user.avatar_url,
    avatar_focal_x: user.avatar_focal_x,
    avatar_focal_y: user.avatar_focal_y,
  }
}

export function withSessionUserInDirectory(
  users: readonly PortalUser[] | undefined,
  sessionUser: AuthUser | null | undefined,
): PortalUser[] {
  const list = users ? [...users] : []
  if (!sessionUser?.sub) {
    return list
  }
  const fromAuth = portalUserFromAuthUser(sessionUser)
  const idx = list.findIndex((u) => u.sub === sessionUser.sub)
  if (idx === -1) {
    return [fromAuth, ...list]
  }
  const existing = list[idx]
  const next: PortalUser = {
    ...existing,
    display_name: existing.display_name || fromAuth.display_name,
    email: existing.email || fromAuth.email,
    username: existing.username || fromAuth.username,
    avatar_url: existing.avatar_url ?? fromAuth.avatar_url,
    avatar_focal_x: existing.avatar_focal_x ?? fromAuth.avatar_focal_x,
    avatar_focal_y: existing.avatar_focal_y ?? fromAuth.avatar_focal_y,
  }
  if (
    next.display_name === existing.display_name &&
    next.email === existing.email &&
    next.username === existing.username &&
    next.avatar_url === existing.avatar_url &&
    next.avatar_focal_x === existing.avatar_focal_x &&
    next.avatar_focal_y === existing.avatar_focal_y
  ) {
    return list
  }
  list[idx] = next
  return list
}
