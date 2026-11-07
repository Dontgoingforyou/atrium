import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'

import type { PortalUserShort } from '../api/usersApi'
import { portalUsersQueryOptions } from '../api/queryKeys'
import { useAuthStore } from '../store/authStore'
import { withSessionUserInDirectory } from '../utils/user/sessionUserInDirectory'
import { getUserDisplayLabel } from '../utils/userLabel'

export type PortalUserAvatarProps = {
  label: string
  imageUrl?: string | null
  focalX?: number | null
  focalY?: number | null
}

/** Кэш пользователей портала для отображения имён и аватаров по sub. */
export function usePortalUserDirectory(options?: { enabled?: boolean; limit?: number }) {
  const enabled = options?.enabled ?? true
  const limit = options?.limit ?? 500

  const sessionUser = useAuthStore((s) => s.user)
  const { data, isPending, isError } = useQuery({
    ...portalUsersQueryOptions(limit),
    enabled,
  })
  const users = useMemo(
    () => withSessionUserInDirectory(data, sessionUser),
    [data, sessionUser],
  )

  const bySub = useMemo(() => {
    const map = new Map<string, PortalUserShort>()
    for (const u of users) {
      map.set(u.sub, u)
    }
    return map
  }, [users])

  function getUser(sub: string | null | undefined): PortalUserShort | undefined {
    if (!sub) return undefined
    return bySub.get(sub)
  }

  function getLabel(sub: string | null | undefined, fallback = '—'): string {
    if (!sub) return fallback
    const u = bySub.get(sub)
    return u ? getUserDisplayLabel(u) : sub
  }

  function getAvatarProps(
    sub: string | null | undefined,
    overrides?: Partial<PortalUserAvatarProps>,
  ): PortalUserAvatarProps {
    const u = sub ? bySub.get(sub) : undefined
    const label = overrides?.label ?? (u ? getUserDisplayLabel(u) : sub || '—')
    return {
      label,
      imageUrl: overrides?.imageUrl ?? u?.avatar_url,
      focalX: overrides?.focalX ?? u?.avatar_focal_x,
      focalY: overrides?.focalY ?? u?.avatar_focal_y,
    }
  }

  return {
    users,
    bySub,
    isPending,
    isError,
    getUser,
    getLabel,
    getAvatarProps,
  }
}
