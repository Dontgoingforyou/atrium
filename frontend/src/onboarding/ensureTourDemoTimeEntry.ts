import {
  createTimeEntry,
  deleteTimeEntry,
  listTimeEntries,
} from '../api/timeEntries/timeEntriesApi'
import type { PortalTimeEntry } from '../types/timeEntry'
import { warnTourCleanupError } from './tourCleanupLog'

export const TOUR_DEMO_TIME_ENTRY_TASK_NAME = 'Учебная запись'
export const TOUR_DEMO_TIME_ENTRY_NOTE =
  'Пример записи для обучения: так фиксируют время за день.'

export type EnsureTourDemoTimeEntriesResult =
  | { ok: true; created: boolean; entryIds: string[] }
  | { ok: false; reason: string }

function isoDateOffsetDays(days: number): string {
  const d = new Date()
  d.setUTCDate(d.getUTCDate() + days)
  return d.toISOString().slice(0, 10)
}

export async function ensureGuidedTourDemoTimeEntries(): Promise<EnsureTourDemoTimeEntriesResult> {
  const existingPage = await listTimeEntries({ limit: 200 })
  const demoEntries = existingPage.items.filter((e) => e.is_tour_demo)
  if (demoEntries.length > 0) {
    return {
      ok: true,
      created: false,
      entryIds: demoEntries.map((e) => e.id),
    }
  }

  const specs = [
    { worked_on: isoDateOffsetDays(0), minutes: 60 },
    { worked_on: isoDateOffsetDays(-1), minutes: 90 },
  ]

  const created: PortalTimeEntry[] = []
  for (const spec of specs) {
    const row = await createTimeEntry({
      worked_on: spec.worked_on,
      minutes: spec.minutes,
      task_name: TOUR_DEMO_TIME_ENTRY_TASK_NAME,
      note: TOUR_DEMO_TIME_ENTRY_NOTE,
      is_tour_demo: true,
    })
    created.push(row)
  }

  return {
    ok: true,
    created: true,
    entryIds: created.map((e) => e.id),
  }
}

/** Удаляет все учебные записи; 404 не считается ошибкой. */
export async function cleanupGuidedTourDemoTimeEntries(entryIds: string[]): Promise<void> {
  await Promise.all(
    entryIds.map(async (id) => {
      try {
        await deleteTimeEntry(id)
      } catch (e) {
        warnTourCleanupError('demo time entry', e)
      }
    }),
  )
}

export { stepNeedsTourDemoTimeEntry } from '../domain/onboarding/guidedTour'
