export const CHANGELOG_SEEN_VERSION_KEY = 'cosmolet_changelog_seen_version'

export function changelogSeenStorageKey(userSub: string): string {
  return `${CHANGELOG_SEEN_VERSION_KEY}:${userSub}`
}
