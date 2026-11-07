import { sanitizeUserAvatarUrl } from './sanitizeUserAvatarUrl'

export function portalUsersAvatarBySub(
  users: ReadonlyArray<{ sub: string; avatar_url?: string | null }>,
): Record<string, string | undefined> {
  return Object.fromEntries(
    users.map((u) => [u.sub, sanitizeUserAvatarUrl(u.avatar_url) ?? undefined]),
  )
}
