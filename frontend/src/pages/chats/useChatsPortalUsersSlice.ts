import { useMemo } from 'react'

import type { PortalUser, UserPresence } from '../../types/chat'
import { portalUsersAvatarBySub } from '../../utils/avatar/portalUsersAvatarBySub'
import { getUserDisplayLabel } from '../../utils/userLabel'
import { filterPortalUsersForPicker } from './filterPortalUsersForPicker'

export function useChatsPortalUsersSlice(
  portalUsers: PortalUser[],
  currentUserSub: string | null,
  pickerSearch: string,
) {
  const userMap: Record<string, string> = useMemo(
    () => Object.fromEntries(portalUsers.map((u) => [u.sub, getUserDisplayLabel(u)])),
    [portalUsers],
  )

  const userAvatarBySub = useMemo(() => portalUsersAvatarBySub(portalUsers), [portalUsers])

  const presenceBySub = useMemo(() => {
    const m: Record<string, UserPresence> = {}
    for (const u of portalUsers) {
      m[u.sub] = u.presence ?? 'offline'
    }
    return m
  }, [portalUsers])

  const lastSeenBySub = useMemo(() => {
    const m: Record<string, string | null> = {}
    for (const u of portalUsers) {
      m[u.sub] = u.last_seen_at ?? null
    }
    return m
  }, [portalUsers])

  const avatarFocalBySub = useMemo(() => {
    const m: Record<string, { x: number; y: number } | undefined> = {}
    for (const u of portalUsers) {
      m[u.sub] =
        u.avatar_focal_x != null && u.avatar_focal_y != null
          ? { x: u.avatar_focal_x, y: u.avatar_focal_y }
          : undefined
    }
    return m
  }, [portalUsers])

  const filteredUsers = useMemo(
    () => filterPortalUsersForPicker(portalUsers, currentUserSub, pickerSearch),
    [portalUsers, currentUserSub, pickerSearch],
  )

  return {
    userMap,
    userAvatarBySub,
    presenceBySub,
    lastSeenBySub,
    avatarFocalBySub,
    filteredUsers,
  }
}
