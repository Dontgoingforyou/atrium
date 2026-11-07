import { describe, expect, it, vi, beforeEach } from 'vitest'

import {
  cleanupGuidedTourDemoSpecialist,
  clearRememberedTourDemoSpecialist,
  ensureGuidedTourDemoSpecialist,
  rememberTourDemoSpecialist,
  resolveTourDemoSpecialistCleanup,
  stepNeedsTourDemoSpecialist,
} from '../../src/onboarding/ensureTourDemoSpecialist'

vi.mock('../../src/api/specialists/specialistsApi', () => ({
  listBoardEntries: vi.fn(),
  listSpecialistColumns: vi.fn(),
  addToBoardApi: vi.fn(),
  removeFromBoardApi: vi.fn(),
}))

vi.mock('../../src/api/usersApi', () => ({
  listPortalStudentSpecialists: vi.fn(),
}))

import {
  addToBoardApi,
  listBoardEntries,
  listSpecialistColumns,
  removeFromBoardApi,
} from '../../src/api/specialists/specialistsApi'
import { listPortalStudentSpecialists } from '../../src/api/usersApi'

describe('ensureGuidedTourDemoSpecialist', () => {
  beforeEach(() => {
    vi.mocked(listBoardEntries).mockReset()
    vi.mocked(listSpecialistColumns).mockReset()
    vi.mocked(addToBoardApi).mockReset()
    vi.mocked(removeFromBoardApi).mockReset()
    vi.mocked(listPortalStudentSpecialists).mockReset()
    clearRememberedTourDemoSpecialist('me')
  })

  it('reuses existing board entry without creating', async () => {
    vi.mocked(listBoardEntries).mockResolvedValue([
      { id: 'e1', specialist_sub: 'stud-1' } as never,
      { id: 'e2', specialist_sub: 'stud-2' } as never,
    ])
    const result = await ensureGuidedTourDemoSpecialist('me')
    expect(result).toEqual({
      ok: true,
      created: false,
      specialistSub: 'stud-1',
      entryId: 'e1',
    })
    expect(listBoardEntries).toHaveBeenCalledWith({ manager_sub: 'me' })
    expect(addToBoardApi).not.toHaveBeenCalled()
  })

  it('treats a single leftover seed card as tour-created', async () => {
    vi.mocked(listBoardEntries).mockResolvedValue([
      { id: 'e1', specialist_sub: 'stud-2' } as never,
    ])
    vi.mocked(listPortalStudentSpecialists).mockResolvedValue({
      items: [{ sub: 'me' } as never, { sub: 'stud-2' } as never],
      total: 2,
      skip: 0,
      limit: 50,
    })
    const result = await ensureGuidedTourDemoSpecialist('me')
    expect(result).toMatchObject({ ok: true, created: true, specialistSub: 'stud-2' })
    expect(addToBoardApi).not.toHaveBeenCalled()
  })

  it('remembers created specialist and resolveTourDemoSpecialistCleanup reads it', () => {
    clearRememberedTourDemoSpecialist('me')
    expect(
      resolveTourDemoSpecialistCleanup({
        demoSpecialistSub: null,
        demoSpecialistCreated: false,
        currentUserSub: 'me',
      }),
    ).toBeNull()
    rememberTourDemoSpecialist('me', 'stud-9')
    expect(
      resolveTourDemoSpecialistCleanup({
        demoSpecialistSub: null,
        demoSpecialistCreated: false,
        currentUserSub: 'me',
      }),
    ).toBe('stud-9')
    expect(
      resolveTourDemoSpecialistCleanup({
        demoSpecialistSub: 'stud-8',
        demoSpecialistCreated: true,
        currentUserSub: 'me',
      }),
    ).toBe('stud-8')
    clearRememberedTourDemoSpecialist('me')
  })

  it('adds first available student to first column when board empty', async () => {
    vi.mocked(listBoardEntries).mockResolvedValue([])
    vi.mocked(listSpecialistColumns).mockResolvedValue([
      { id: 'c2', key: 'screening', title: 'Скрининг', color: '#0', position: 2 } as never,
      { id: 'c1', key: 'newbies', title: 'Новички', color: '#0', position: 1 } as never,
    ])
    vi.mocked(listPortalStudentSpecialists).mockResolvedValue({
      items: [{ sub: 'me' } as never, { sub: 'stud-2' } as never],
      total: 2,
      skip: 0,
      limit: 50,
    })
    vi.mocked(addToBoardApi).mockResolvedValue({
      id: 'e-new',
      specialist_sub: 'stud-2',
    } as never)

    const result = await ensureGuidedTourDemoSpecialist('me')
    expect(result).toEqual({
      ok: true,
      created: true,
      specialistSub: 'stud-2',
      entryId: 'e-new',
    })
    expect(addToBoardApi).toHaveBeenCalledWith(
      {
        specialist_sub: 'stud-2',
        column_key: 'newbies',
      },
      { manager_sub: 'me' },
    )
  })

  it('fails when no students and board empty', async () => {
    vi.mocked(listBoardEntries).mockResolvedValue([])
    vi.mocked(listSpecialistColumns).mockResolvedValue([
      { id: 'c1', key: 'newbies', title: 'Новички', color: '#0', position: 0 } as never,
    ])
    vi.mocked(listPortalStudentSpecialists).mockResolvedValue({
      items: [],
      total: 0,
      skip: 0,
      limit: 50,
    })
    const result = await ensureGuidedTourDemoSpecialist('me')
    expect(result.ok).toBe(false)
    expect(addToBoardApi).not.toHaveBeenCalled()
  })

  it('fails without current user', async () => {
    const result = await ensureGuidedTourDemoSpecialist('')
    expect(result.ok).toBe(false)
    expect(listBoardEntries).not.toHaveBeenCalled()
    expect(addToBoardApi).not.toHaveBeenCalled()
  })

  it('предпочитает чужого студента, не текущего user', async () => {
    vi.mocked(listBoardEntries).mockResolvedValue([])
    vi.mocked(listSpecialistColumns).mockResolvedValue([
      { id: 'c1', key: 'newbies', title: 'Новички', color: '#0', position: 0 } as never,
    ])
    vi.mocked(listPortalStudentSpecialists).mockResolvedValue({
      items: [{ sub: 'me' } as never, { sub: 'stud-9' } as never],
      total: 2,
      skip: 0,
      limit: 50,
    })
    vi.mocked(addToBoardApi).mockResolvedValue({
      id: 'e-new',
      specialist_sub: 'stud-9',
    } as never)
    await ensureGuidedTourDemoSpecialist('me')
    expect(addToBoardApi).toHaveBeenCalledWith(
      expect.objectContaining({ specialist_sub: 'stud-9' }),
      { manager_sub: 'me' },
    )
  })

  it('cleanup swallows remove errors', async () => {
    vi.mocked(removeFromBoardApi).mockRejectedValue(new Error('gone'))
    await expect(cleanupGuidedTourDemoSpecialist('x', 'me')).resolves.toBeUndefined()
  })

  it('stepNeedsTourDemoSpecialist detects specialist board steps', () => {
    expect(stepNeedsTourDemoSpecialist({ id: 'specialists-kanban-card' })).toBe(true)
    expect(stepNeedsTourDemoSpecialist({ id: 'specialists-kanban-column-header' })).toBe(true)
    expect(stepNeedsTourDemoSpecialist({ id: 'specialists-detail' })).toBe(true)
    expect(stepNeedsTourDemoSpecialist({ id: 'tasks-kanban-card' })).toBe(false)
  })
})
