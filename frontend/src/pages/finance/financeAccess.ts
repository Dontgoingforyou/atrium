import { isUserManagerOrAdmin } from '../../domain/auth/authRoles'
import type { AuthUser } from '../../types/auth'

/** Автор записи или администратор портала — как на бэкенде для patch/delete. */
export function canMutateOwnedFinanceRecord(
  authorSub: string,
  user: Pick<AuthUser, 'sub' | 'is_portal_admin'> | null | undefined,
): boolean {
  if (!user) return false
  return user.is_portal_admin || user.sub === authorSub
}

/** Создание закупочной заявки: менеджер/admin (роль «Закупщик» на бэкенде). */
export function canCreateProcurementRequest(user: AuthUser | null | undefined): boolean {
  if (!user) return false
  return isUserManagerOrAdmin(user)
}
