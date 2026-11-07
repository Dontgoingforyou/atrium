/** Ключи React Query для экрана календаря. */
export const calendarQueryKeys = {
  all: ['portal', 'calendar'] as const,
  calendars: ['portal', 'calendar', 'calendars'] as const,
  shared: ['portal', 'calendar', 'calendars', 'shared'] as const,
  occurrencesRoot: ['portal', 'calendar', 'occurrences'] as const,
  occurrences: (from: string, to: string, calendarIds: string[], peerUserSub?: string | null) =>
    [
      'portal',
      'calendar',
      'occurrences',
      from,
      to,
      calendarIds.join(','),
      peerUserSub ?? '',
    ] as const,
  search: (q: string) => ['portal', 'calendar', 'events', 'search', q] as const,
  peerContext: (peerUserSub: string) => ['portal', 'calendar', 'peer-context', peerUserSub] as const,
}
