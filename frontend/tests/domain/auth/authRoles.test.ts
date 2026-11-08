import { describe, expect, it } from 'vitest'

import {
  IDP_GROUP_DEVELOPER,
  IDP_GROUP_OUTSTAFF,
  IDP_GROUP_PORTAL_ADMIN,
  SSO_GID_OUTSTAFF,
  SSO_POSITION_AU_SPECIALIST,
  SSO_POSITION_STUDENT,
  isTimesheetOnlyUser,
  isUserDeveloper,
  isUserDeveloperOnly,
  isUserManagerOrAdmin,
  type PortalAuthRoleInput,
} from '@/domain/auth/authRoles'

function role(
  idpGroups: string[],
  isPortalAdmin: boolean,
  position?: string | null,
  gidNumber?: string | number | null,
): PortalAuthRoleInput {
  return {
    idp_groups: idpGroups,
    is_portal_admin: isPortalAdmin,
    position,
    gid_number: gidNumber,
  }
}

describe('isUserDeveloper', () => {
  it('возвращает true для группы students', () => {
    expect(isUserDeveloper([IDP_GROUP_DEVELOPER])).toBe(true)
  })

  it('возвращает false без группы students', () => {
    expect(isUserDeveloper([IDP_GROUP_OUTSTAFF])).toBe(false)
    expect(isUserDeveloper([])).toBe(false)
  })
})

describe('isUserManagerOrAdmin', () => {
  it('true если is_portal_admin=true', () => {
    expect(isUserManagerOrAdmin(role([], true))).toBe(true)
  })

  it('true если основной отдел Аутстафф (gid 10000)', () => {
    expect(isUserManagerOrAdmin(role([IDP_GROUP_OUTSTAFF], false, null, SSO_GID_OUTSTAFF))).toBe(true)
    expect(isUserManagerOrAdmin(role([], false, 'au_chief', 10000))).toBe(true)
  })

  it('false если группа outstaff, но отдел не Аутстафф', () => {
    expect(isUserManagerOrAdmin(role([IDP_GROUP_OUTSTAFF], false, 'au_chief', '10001'))).toBe(false)
    expect(isUserManagerOrAdmin(role([IDP_GROUP_OUTSTAFF], false))).toBe(false)
  })

  it('false для au_specialist даже с gid 10000', () => {
    expect(
      isUserManagerOrAdmin(role([IDP_GROUP_OUTSTAFF], false, SSO_POSITION_AU_SPECIALIST, SSO_GID_OUTSTAFF)),
    ).toBe(false)
  })

  it('false для position=student даже с gid 10000', () => {
    expect(
      isUserManagerOrAdmin(role([], false, SSO_POSITION_STUDENT, SSO_GID_OUTSTAFF)),
    ).toBe(false)
  })

  it('true при gid с пробелами (trim)', () => {
    expect(isUserManagerOrAdmin(role([], false, null, ' 10000 '))).toBe(true)
  })

  it('false при пустом gid_number', () => {
    expect(isUserManagerOrAdmin(role([IDP_GROUP_OUTSTAFF], false, null, ''))).toBe(false)
  })

  it('IdP-группа portal_admin без флага is_portal_admin — не менеджер', () => {
    expect(isUserManagerOrAdmin(role([IDP_GROUP_PORTAL_ADMIN], false))).toBe(false)
  })

  it('false без прав менеджера/админа', () => {
    expect(isUserManagerOrAdmin(role([IDP_GROUP_DEVELOPER], false))).toBe(false)
    expect(isUserManagerOrAdmin(role([], false))).toBe(false)
  })
})

describe('isTimesheetOnlyUser', () => {
  it('true — только студент, без менеджера и без admin', () => {
    expect(isTimesheetOnlyUser(role([IDP_GROUP_DEVELOPER], false))).toBe(true)
  })

  it('false — студент + отдел Аутстафф: приоритет старшей роли', () => {
    expect(
      isTimesheetOnlyUser(role([IDP_GROUP_DEVELOPER, IDP_GROUP_OUTSTAFF], false, null, SSO_GID_OUTSTAFF)),
    ).toBe(false)
  })

  it('true — студент + группа outstaff без gid Аутстаффа', () => {
    expect(isTimesheetOnlyUser(role([IDP_GROUP_DEVELOPER, IDP_GROUP_OUTSTAFF], false))).toBe(true)
  })

  it('true — au_specialist с отделом Аутстафф: должность ограничивает доступ', () => {
    expect(
      isTimesheetOnlyUser(
        role([IDP_GROUP_DEVELOPER, IDP_GROUP_OUTSTAFF], false, SSO_POSITION_AU_SPECIALIST, SSO_GID_OUTSTAFF),
      ),
    ).toBe(true)
    expect(
      isUserManagerOrAdmin(
        role([IDP_GROUP_DEVELOPER, IDP_GROUP_OUTSTAFF], false, SSO_POSITION_AU_SPECIALIST, SSO_GID_OUTSTAFF),
      ),
    ).toBe(false)
  })

  it('true — position=student без students-группы (должность важнее)', () => {
    expect(isTimesheetOnlyUser(role([], false, SSO_POSITION_STUDENT, SSO_GID_OUTSTAFF))).toBe(true)
    expect(isUserManagerOrAdmin(role([], false, SSO_POSITION_STUDENT, SSO_GID_OUTSTAFF))).toBe(false)
  })

  it('false — student + is_portal_admin: admin short-circuit', () => {
    expect(isTimesheetOnlyUser(role([], true, SSO_POSITION_STUDENT, SSO_GID_OUTSTAFF))).toBe(false)
    expect(isUserManagerOrAdmin(role([], true, SSO_POSITION_STUDENT, SSO_GID_OUTSTAFF))).toBe(true)
  })

  it('false — менеджер отдела students + outstaff + au_chief + gid 10000', () => {
    expect(
      isTimesheetOnlyUser(role([IDP_GROUP_DEVELOPER, IDP_GROUP_OUTSTAFF], false, 'au_chief', SSO_GID_OUTSTAFF)),
    ).toBe(false)
    expect(
      isUserManagerOrAdmin(role([IDP_GROUP_DEVELOPER, IDP_GROUP_OUTSTAFF], false, 'au_chief', SSO_GID_OUTSTAFF)),
    ).toBe(true)
  })

  it('false — студент + is_portal_admin: приоритет старшей роли', () => {
    expect(isTimesheetOnlyUser(role([IDP_GROUP_DEVELOPER], true))).toBe(false)
  })

  it('false — студент + все роли одновременно', () => {
    expect(
      isTimesheetOnlyUser(
        role([IDP_GROUP_DEVELOPER, IDP_GROUP_OUTSTAFF, IDP_GROUP_PORTAL_ADMIN], true, null, SSO_GID_OUTSTAFF),
      ),
    ).toBe(false)
  })

  it('false — не студент вообще', () => {
    expect(isTimesheetOnlyUser(role([], false))).toBe(false)
    expect(isTimesheetOnlyUser(role([IDP_GROUP_OUTSTAFF], false))).toBe(false)
  })
})

describe('isUserDeveloperOnly (alias)', () => {
  it('совпадает с isTimesheetOnlyUser', () => {
    expect(isUserDeveloperOnly(role([IDP_GROUP_DEVELOPER], false))).toBe(
      isTimesheetOnlyUser(role([IDP_GROUP_DEVELOPER], false)),
    )
  })
})
