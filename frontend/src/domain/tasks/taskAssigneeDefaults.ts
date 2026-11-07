/** Исполнители по умолчанию при создании задачи с доски. */
export function resolveDefaultTaskAssigneeSubs(
  scope: 'my' | 'team',
  filterAssigneeSubs: readonly string[],
  currentUserSub: string | undefined,
): string[] {
  if (scope === 'team' && filterAssigneeSubs.length > 0) {
    return [...filterAssigneeSubs]
  }
  return currentUserSub ? [currentUserSub] : []
}
