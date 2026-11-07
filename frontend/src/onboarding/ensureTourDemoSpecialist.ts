import { listPortalStudentSpecialists } from '../api/usersApi'
import {
  addToBoardApi,
  listBoardEntries,
  listSpecialistColumns,
  removeFromBoardApi,
} from '../api/specialists/specialistsApi'
import { warnTourCleanupError } from './tourCleanupLog'

export type EnsureTourDemoSpecialistResult =
  | {
      ok: true
      created: boolean
      specialistSub: string
      entryId: string
    }
  | { ok: false; reason: string }

const tourDemoSpecialistStorageKey = (userSub: string): string =>
  `cosmolet.guidedTour.demoSpecialist:${userSub}`

const rememberedByUser = new Map<string, string>()

export function rememberTourDemoSpecialist(userSub: string, specialistSub: string): void {
  rememberedByUser.set(userSub, specialistSub)
  if (typeof sessionStorage === 'undefined') return
  try {
    sessionStorage.setItem(tourDemoSpecialistStorageKey(userSub), specialistSub)
  } catch {
    // quota / private mode — достаточно памяти сессии
  }
}

export function readRememberedTourDemoSpecialist(userSub: string): string | null {
  const fromMem = rememberedByUser.get(userSub)
  if (fromMem) return fromMem
  if (typeof sessionStorage === 'undefined') return null
  try {
    return sessionStorage.getItem(tourDemoSpecialistStorageKey(userSub))
  } catch {
    return null
  }
}

export function clearRememberedTourDemoSpecialist(userSub: string): void {
  rememberedByUser.delete(userSub)
  if (typeof sessionStorage === 'undefined') return
  try {
    sessionStorage.removeItem(tourDemoSpecialistStorageKey(userSub))
  } catch {
    // ignore
  }
}

/**
 * Гарантирует карточку на доске специалистов для онбординга.
 * Если доска пуста — добавляет первого доступного студента в первую колонку.
 * Удалять при cleanup можно только запись, созданную этим ensure (created: true).
 */
export async function ensureGuidedTourDemoSpecialist(
  currentUserSub: string,
): Promise<EnsureTourDemoSpecialistResult> {
  if (!currentUserSub) {
    return {
      ok: false,
      reason: 'Не удалось подготовить учебного специалиста: пользователь не определён.',
    }
  }

  const entries = await listBoardEntries({ manager_sub: currentUserSub })
  const remembered = readRememberedTourDemoSpecialist(currentUserSub)
  if (entries.length > 0) {
    const owned = remembered
      ? entries.find((e) => e.specialist_sub === remembered)
      : undefined
    if (owned) {
      return {
        ok: true,
        created: true,
        specialistSub: owned.specialist_sub,
        entryId: owned.id,
      }
    }
    if (entries.length === 1) {
      const only = entries[0]!
      const page = await listPortalStudentSpecialists({ limit: 50, skip: 0 })
      const candidate =
        page.items.find((u) => u.sub !== currentUserSub) ?? page.items[0] ?? null
      // Пустая доска + первый студент из справочника — типичный след прошлого тура без cleanup.
      if (candidate && only.specialist_sub === candidate.sub) {
        rememberTourDemoSpecialist(currentUserSub, only.specialist_sub)
        return {
          ok: true,
          created: true,
          specialistSub: only.specialist_sub,
          entryId: only.id,
        }
      }
    }
    const first = entries[0]!
    return {
      ok: true,
      created: false,
      specialistSub: first.specialist_sub,
      entryId: first.id,
    }
  }

  const columns = await listSpecialistColumns()
  const sorted = [...columns].sort((a, b) => a.position - b.position)
  const firstCol = sorted[0]
  if (!firstCol) {
    return {
      ok: false,
      reason: 'Не удалось подготовить учебного специалиста: на доске нет колонок.',
    }
  }

  const page = await listPortalStudentSpecialists({ limit: 50, skip: 0 })
  const candidate =
    page.items.find((u) => u.sub !== currentUserSub) ?? page.items[0] ?? null
  if (!candidate) {
    return {
      ok: false,
      reason:
        'Не удалось подготовить учебного специалиста: в справочнике нет специалистов для добавления на доску.',
    }
  }

  const entry = await addToBoardApi(
    {
      specialist_sub: candidate.sub,
      column_key: firstCol.key,
    },
    { manager_sub: currentUserSub },
  )

  rememberTourDemoSpecialist(currentUserSub, entry.specialist_sub)
  return {
    ok: true,
    created: true,
    specialistSub: entry.specialist_sub,
    entryId: entry.id,
  }
}

/** Убирает с доски учебную запись; 404 не блокирует завершение. */
export async function cleanupGuidedTourDemoSpecialist(
  specialistSub: string,
  managerSub?: string,
): Promise<void> {
  try {
    await removeFromBoardApi(
      specialistSub,
      managerSub ? { manager_sub: managerSub } : undefined,
    )
  } catch (e) {
    warnTourCleanupError('demo specialist', e)
  }
  if (managerSub) {
    clearRememberedTourDemoSpecialist(managerSub)
  }
}

/** Кого снимать с доски после тура: флаг сессии или запомненный sub. */
export function resolveTourDemoSpecialistCleanup(args: {
  demoSpecialistSub: string | null
  demoSpecialistCreated: boolean
  currentUserSub?: string
}): string | null {
  if (args.demoSpecialistCreated && args.demoSpecialistSub) {
    return args.demoSpecialistSub
  }
  if (args.currentUserSub) {
    return readRememberedTourDemoSpecialist(args.currentUserSub)
  }
  return null
}

export { stepNeedsTourDemoSpecialist } from '../domain/onboarding/guidedTour'
