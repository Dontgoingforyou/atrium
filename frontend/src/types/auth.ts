/** DTO аутентифицированного пользователя портала (ответы /auth/me, /auth/token, /auth/refresh). */

export interface AuthUser {
  sub: string
  email: string
  username: string
  full_name: string
  idp_groups: string[]
  is_portal_admin: boolean
  position?: string | null
  gid_number?: string | null
  avatar_url?: string | null
  avatar_focal_x?: number | null
  avatar_focal_y?: number | null
}
