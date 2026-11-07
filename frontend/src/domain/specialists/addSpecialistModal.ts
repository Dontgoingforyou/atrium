export type AddSpecialistModalAction = 'add' | 'move'

export type AddSpecialistModalCandidate = {
  sub: string
  display_name?: string | null
  email?: string | null
  username?: string | null
  avatar_url?: string | null
}

export type AddSpecialistModalRow = {
  student: AddSpecialistModalCandidate
  action: AddSpecialistModalAction
}

export function specialistMatchesModalSearch(
  user: AddSpecialistModalCandidate,
  search: string,
): boolean {
  const q = search.toLowerCase().trim()
  if (!q) return true
  return (
    (user.display_name ?? '').toLowerCase().includes(q) ||
    (user.email ?? '').toLowerCase().includes(q) ||
    (user.username ?? '').toLowerCase().includes(q)
  )
}

export function listAddSpecialistModalRows(
  specialists: readonly AddSpecialistModalCandidate[],
  alreadyAddedSubs: ReadonlySet<string>,
  search: string,
): AddSpecialistModalRow[] {
  return specialists.filter((user) => specialistMatchesModalSearch(user, search)).map((student) => ({
    student,
    action: alreadyAddedSubs.has(student.sub) ? 'move' : 'add',
  }))
}
