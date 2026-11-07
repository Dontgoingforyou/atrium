import type { PortalUser } from '../../types/user'
import { getUserDisplayLabel } from '../userLabel'

/** Фильтр кандидатов @-упоминания по подстроке (без жёсткого лимита списка). */
export function filterMentionUsers(users: PortalUser[], query: string): PortalUser[] {
  const needle = query.toLowerCase()
  return users.filter((user) => getUserDisplayLabel(user).toLowerCase().includes(needle))
}
