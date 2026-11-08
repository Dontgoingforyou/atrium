export const GUIDED_TOUR_SEEN_STEPS_KEY_PREFIX = 'atrium_guided_tour_seen_steps'

export function guidedTourSeenStepsStorageKey(userSub: string): string {
  return `${GUIDED_TOUR_SEEN_STEPS_KEY_PREFIX}:${userSub}`
}
