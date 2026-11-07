/** Публичный профиль пользователя портала (список users / чат / пикеры). */

export type UserPresence = 'offline' | 'online' | 'away'

export type PortalUser = {
  sub: string
  display_name: string | null
  email: string | null
  username: string | null
  presence?: UserPresence
  avatar_url?: string | null
  last_seen_at?: string | null
  /** Центр кадра аватара 0–1; для object-position */
  avatar_focal_x?: number | null
  avatar_focal_y?: number | null
}

/** @deprecated Используйте PortalUser — алиас для обратной совместимости импортов из usersApi. */
export type PortalUserShort = PortalUser
