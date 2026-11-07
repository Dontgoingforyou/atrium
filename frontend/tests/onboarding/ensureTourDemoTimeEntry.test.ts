import { describe, expect, it, vi, beforeEach } from 'vitest'

import {
  cleanupGuidedTourDemoTimeEntries,
  ensureGuidedTourDemoTimeEntries,
  stepNeedsTourDemoTimeEntry,
  TOUR_DEMO_TIME_ENTRY_NOTE,
  TOUR_DEMO_TIME_ENTRY_TASK_NAME,
} from '../../src/onboarding/ensureTourDemoTimeEntry'

vi.mock('../../src/api/timeEntries/timeEntriesApi', () => ({
  listTimeEntries: vi.fn(),
  createTimeEntry: vi.fn(),
  deleteTimeEntry: vi.fn(),
}))

import {
  createTimeEntry,
  deleteTimeEntry,
  listTimeEntries,
} from '../../src/api/timeEntries/timeEntriesApi'

describe('ensureGuidedTourDemoTimeEntries', () => {
  beforeEach(() => {
    vi.mocked(listTimeEntries).mockReset()
    vi.mocked(createTimeEntry).mockReset()
    vi.mocked(deleteTimeEntry).mockReset()
  })

  it('reuses existing tour-demo entries', async () => {
    vi.mocked(listTimeEntries).mockResolvedValue({
      items: [
        { id: 'te1', is_tour_demo: true } as never,
        { id: 'te2', is_tour_demo: true } as never,
        { id: 'te3', is_tour_demo: false } as never,
      ],
      total: 3,
      skip: 0,
      limit: 200,
    })
    const result = await ensureGuidedTourDemoTimeEntries()
    expect(result).toEqual({ ok: true, created: false, entryIds: ['te1', 'te2'] })
    expect(createTimeEntry).not.toHaveBeenCalled()
  })

  it('creates two entries when none exist', async () => {
    vi.mocked(listTimeEntries).mockResolvedValue({ items: [], total: 0, skip: 0, limit: 200 })
    vi.mocked(createTimeEntry)
      .mockResolvedValueOnce({ id: 'new1' } as never)
      .mockResolvedValueOnce({ id: 'new2' } as never)

    const result = await ensureGuidedTourDemoTimeEntries()
    expect(result).toEqual({ ok: true, created: true, entryIds: ['new1', 'new2'] })
    expect(createTimeEntry).toHaveBeenCalledTimes(2)
    expect(createTimeEntry).toHaveBeenCalledWith(
      expect.objectContaining({
        task_name: TOUR_DEMO_TIME_ENTRY_TASK_NAME,
        note: TOUR_DEMO_TIME_ENTRY_NOTE,
        is_tour_demo: true,
      }),
    )
  })

  it('создаёт демо, если есть только обычные записи (не is_tour_demo)', async () => {
    vi.mocked(listTimeEntries).mockResolvedValue({
      items: [{ id: 'real', is_tour_demo: false } as never],
      total: 1,
      skip: 0,
      limit: 200,
    })
    vi.mocked(createTimeEntry)
      .mockResolvedValueOnce({ id: 'new1' } as never)
      .mockResolvedValueOnce({ id: 'new2' } as never)
    const result = await ensureGuidedTourDemoTimeEntries()
    expect(result).toMatchObject({ ok: true, created: true })
    expect(createTimeEntry).toHaveBeenCalledTimes(2)
  })

  it('cleanup с пустым списком — без delete', async () => {
    await cleanupGuidedTourDemoTimeEntries([])
    expect(deleteTimeEntry).not.toHaveBeenCalled()
  })

  it('cleanup swallows delete errors', async () => {
    vi.mocked(deleteTimeEntry).mockRejectedValue(new Error('gone'))
    await expect(cleanupGuidedTourDemoTimeEntries(['x', 'y'])).resolves.toBeUndefined()
    expect(deleteTimeEntry).toHaveBeenCalledTimes(2)
  })

  it('stepNeedsTourDemoTimeEntry detects timesheet steps', () => {
    expect(stepNeedsTourDemoTimeEntry({ id: 'timesheets-summary' })).toBe(true)
    expect(stepNeedsTourDemoTimeEntry({ id: 'timesheets-entries' })).toBe(true)
    expect(stepNeedsTourDemoTimeEntry({ id: 'timesheets-report' })).toBe(true)
    expect(stepNeedsTourDemoTimeEntry({ id: 'calendar-grid' })).toBe(false)
  })
})
