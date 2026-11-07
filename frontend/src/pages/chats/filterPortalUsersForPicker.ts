import type { PortalUser } from '../../types/chat'

export function filterPortalUsersForPicker(
  portalUsers: PortalUser[],
  currentUserSub: string | null,
  pickerSearch: string,
): PortalUser[] {
  const q = pickerSearch.trim().toLowerCase()
  return portalUsers.filter(
    (u) =>
      u.sub !== currentUserSub &&
      (!q ||
        (u.display_name ?? '').toLowerCase().includes(q) ||
        (u.email ?? '').toLowerCase().includes(q) ||
        (u.username ?? '').toLowerCase().includes(q)),
  )
}
