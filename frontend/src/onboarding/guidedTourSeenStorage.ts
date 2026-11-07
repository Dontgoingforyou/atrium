import { guidedTourSeenStepsStorageKey } from '../constants/guidedTour'

function storage(): Storage | null {
  try {
    if (typeof localStorage === 'undefined') return null
    return localStorage
  } catch {
    return null
  }
}

function normalizeUserSub(userSub: string): string | null {
  const trimmed = userSub.trim()
  return trimmed.length > 0 ? trimmed : null
}

function parseSeenIds(raw: string | null): string[] {
  if (!raw) return []
  try {
    const parsed: unknown = JSON.parse(raw)
    if (!Array.isArray(parsed)) return []
    return parsed.filter((item): item is string => typeof item === 'string' && item.length > 0)
  } catch {
    return []
  }
}

export function readGuidedTourSeenStepIds(userSub: string): Set<string> {
  const sub = normalizeUserSub(userSub)
  const store = storage()
  if (!sub || !store) return new Set()
  return new Set(parseSeenIds(store.getItem(guidedTourSeenStepsStorageKey(sub))))
}

export function writeGuidedTourSeenStepIds(userSub: string, ids: readonly string[]): void {
  const sub = normalizeUserSub(userSub)
  const store = storage()
  if (!sub || !store) return
  const unique = [...new Set(ids.filter((id) => id.length > 0))]
  store.setItem(guidedTourSeenStepsStorageKey(sub), JSON.stringify(unique))
}

export function addGuidedTourSeenStepIds(userSub: string, ids: readonly string[]): void {
  const current = readGuidedTourSeenStepIds(userSub)
  for (const id of ids) {
    if (id) current.add(id)
  }
  writeGuidedTourSeenStepIds(userSub, [...current])
}

export function clearGuidedTourSeenStepIds(userSub: string): void {
  const sub = normalizeUserSub(userSub)
  const store = storage()
  if (!sub || !store) return
  store.removeItem(guidedTourSeenStepsStorageKey(sub))
}
