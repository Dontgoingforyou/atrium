import { describe, expect, it } from 'vitest'
import { canCreateProcurementRequest, canMutateOwnedFinanceRecord } from '../../../src/pages/finance/financeAccess'
import { SSO_GID_OUTSTAFF, SSO_POSITION_AU_SPECIALIST, SSO_POSITION_STUDENT } from '../../../src/domain/auth/authRoles'
import type { AuthUser } from '../../../src/types/auth'

function user(over: Partial<AuthUser>): AuthUser {
  return {
    sub: 'u1',
    email: 'a@b.c',
    username: 'u',
    full_name: 'U',
    idp_groups: [],
    is_portal_admin: false,
    ...over,
  }
}

describe('canMutateOwnedFinanceRecord', () => {
  it('отказывает без пользователя', () => {
    expect(canMutateOwnedFinanceRecord('u1', null)).toBe(false)
    expect(canMutateOwnedFinanceRecord('u1', undefined)).toBe(false)
  })

  it('разрешает автору', () => {
    expect(canMutateOwnedFinanceRecord('u1', user({ sub: 'u1' }))).toBe(true)
  })

  it('разрешает админу чужую запись', () => {
    expect(canMutateOwnedFinanceRecord('other', user({ is_portal_admin: true }))).toBe(true)
  })

  it('запрещает чужую запись обычному пользователю', () => {
    expect(canMutateOwnedFinanceRecord('other', user({ sub: 'u1' }))).toBe(false)
  })

  it('менеджер отдела не мутирует чужую запись (только author|admin)', () => {
    expect(
      canMutateOwnedFinanceRecord('other', user({ sub: 'u1', gid_number: SSO_GID_OUTSTAFF })),
    ).toBe(false)
  })
})

describe('canCreateProcurementRequest', () => {
  it('отказывает без пользователя', () => {
    expect(canCreateProcurementRequest(null)).toBe(false)
    expect(canCreateProcurementRequest(undefined)).toBe(false)
  })

  it('разрешает админу', () => {
    expect(canCreateProcurementRequest(user({ is_portal_admin: true }))).toBe(true)
  })

  it('разрешает менеджеру отдела Аутстафф', () => {
    expect(canCreateProcurementRequest(user({ gid_number: SSO_GID_OUTSTAFF }))).toBe(true)
  })

  it('запрещает обычному пользователю', () => {
    expect(canCreateProcurementRequest(user({}))).toBe(false)
  })

  it('запрещает timesheet-only (au_specialist / student) даже с gid Аутстафф', () => {
    expect(
      canCreateProcurementRequest(
        user({ gid_number: SSO_GID_OUTSTAFF, position: SSO_POSITION_AU_SPECIALIST }),
      ),
    ).toBe(false)
    expect(
      canCreateProcurementRequest(
        user({ gid_number: SSO_GID_OUTSTAFF, position: SSO_POSITION_STUDENT }),
      ),
    ).toBe(false)
  })
})
