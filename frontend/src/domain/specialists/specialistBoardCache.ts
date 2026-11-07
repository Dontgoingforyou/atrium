import type { QueryClient } from '@tanstack/react-query'

import type { ManagerSpecialistEntry } from '../../types/specialist'

export const QK_BOARD_ROOT = ['portal', 'specialists', 'board'] as const
export const QK_COLUMNS = ['portal', 'specialists', 'columns'] as const
export const QK_PREF = ['portal', 'specialists', 'board-pref'] as const

export type BoardScopeKey = 'my' | 'all'

export function specialistBoardQueryKey(
  scopeKey: BoardScopeKey,
  userSub: string | undefined,
): readonly [...typeof QK_BOARD_ROOT, BoardScopeKey, string | undefined] {
  return [...QK_BOARD_ROOT, scopeKey, userSub]
}

export function specialistBoardQueryKeys(
  userSub: string | undefined,
): readonly [
  ReturnType<typeof specialistBoardQueryKey>,
  ReturnType<typeof specialistBoardQueryKey>,
] {
  return [specialistBoardQueryKey('my', userSub), specialistBoardQueryKey('all', userSub)]
}

/** Снять закрепление одного менеджера; остальные менеджеры того же специалиста остаются. */
export function withoutBoardAttachment(
  entries: ManagerSpecialistEntry[],
  specialistSub: string,
  managerSub: string,
): ManagerSpecialistEntry[] {
  return entries.filter(
    (e) => !(e.specialist_sub === specialistSub && e.manager_sub === managerSub),
  )
}

export function patchAllSpecialistBoardCaches(
  queryClient: QueryClient,
  userSub: string | undefined,
  updater: (prev: ManagerSpecialistEntry[]) => ManagerSpecialistEntry[],
): void {
  for (const key of specialistBoardQueryKeys(userSub)) {
    queryClient.setQueryData<ManagerSpecialistEntry[]>(key, (prev) =>
      prev ? updater(prev) : prev,
    )
  }
}

export function snapshotSpecialistBoardCaches(
  queryClient: QueryClient,
  userSub: string | undefined,
): Map<string, ManagerSpecialistEntry[] | undefined> {
  const snap = new Map<string, ManagerSpecialistEntry[] | undefined>()
  for (const key of specialistBoardQueryKeys(userSub)) {
    snap.set(JSON.stringify(key), queryClient.getQueryData<ManagerSpecialistEntry[]>(key))
  }
  return snap
}

export function restoreSpecialistBoardCaches(
  queryClient: QueryClient,
  snapshot: Map<string, ManagerSpecialistEntry[] | undefined>,
): void {
  for (const [keyJson, data] of snapshot) {
    queryClient.setQueryData(JSON.parse(keyJson) as readonly string[], data)
  }
}
