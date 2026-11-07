/** Константы ролей — синхронизированы с backend/app/core/auth_constants.py */
export const IDP_GROUP_PORTAL_ADMIN = 'cosmolet_role_admin'
/** IdP-метка отдела «Аутстафф» (группа Keycloak). Не политика менеджера — та по gid_number. */
export const IDP_GROUP_OUTSTAFF = 'outstaff'
/** IDP-группа «students» в Keycloak; в коде — «developer» (историческое название). */
export const IDP_GROUP_DEVELOPER = 'students'

/** Должности SSO (claim position) с доступом только к таймшитам. */
export const SSO_POSITION_AU_SPECIALIST = 'au_specialist'
export const SSO_POSITION_STUDENT = 'student'

/** Основной отдел SSO (claim gid_number): «Аутстафф» / АУ. */
export const SSO_GID_OUTSTAFF = '10000'

const TIMESHEET_ONLY_POSITIONS = new Set([SSO_POSITION_AU_SPECIALIST, SSO_POSITION_STUDENT])

export type PortalAuthRoleInput = {
  idp_groups: string[]
  is_portal_admin: boolean
  position?: string | null
  gid_number?: string | number | null
}

function isOutstaffDepartment(gidNumber?: string | number | null): boolean {
  if (gidNumber == null || gidNumber === '') return false
  return String(gidNumber).trim() === SSO_GID_OUTSTAFF
}

/** Пользователь группы students (без учёта должности и менеджера). */
export function isUserDeveloper(idpGroups: string[]): boolean {
  return idpGroups.includes(IDP_GROUP_DEVELOPER)
}

/** Менеджер или выше: основной отдел Аутстафф (gid_number=10000); должности «только ТШ» отменяют доступ. */
export function isUserManagerOrAdmin(user: PortalAuthRoleInput): boolean {
  if (user.is_portal_admin) return true
  if (user.position && TIMESHEET_ONLY_POSITIONS.has(user.position)) return false
  return isOutstaffDepartment(user.gid_number)
}

/**
 * Доступ только к таймшитам: по должности SSO или legacy students без менеджера/admin.
 * При наличии нескольких ролей (students + отдел Аутстафф / admin) приоритет у старшей роли,
 * кроме должностей из TIMESHEET_ONLY_POSITIONS (например au_specialist).
 */
export function isTimesheetOnlyUser(user: PortalAuthRoleInput): boolean {
  if (user.is_portal_admin) return false
  if (user.position && TIMESHEET_ONLY_POSITIONS.has(user.position)) return true
  return idpGroupsHasDeveloper(user.idp_groups) && !isUserManagerOrAdmin(user)
}

function idpGroupsHasDeveloper(idpGroups: string[]): boolean {
  return idpGroups.includes(IDP_GROUP_DEVELOPER)
}

/** @deprecated Используйте isTimesheetOnlyUser — сохранено для совместимости вызовов. */
export function isUserDeveloperOnly(user: PortalAuthRoleInput): boolean {
  return isTimesheetOnlyUser(user)
}
