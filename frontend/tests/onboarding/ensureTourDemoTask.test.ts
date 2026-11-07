import { describe, expect, it, vi, beforeEach } from 'vitest'

import {
  buildTourDemoTaskPrefill,
  cleanupGuidedTourDemoTask,
  ensureGuidedTourDemoTask,
  stepNeedsTourDemoTask,
  TOUR_DEMO_TASK_DESCRIPTION,
  TOUR_DEMO_TASK_TITLE,
} from '../../src/onboarding/ensureTourDemoTask'

vi.mock('../../src/api/tasks/tasksApi', () => ({
  listTasks: vi.fn(),
  createTask: vi.fn(),
  deleteTask: vi.fn(),
}))

vi.mock('../../src/api/tags/tagsApi', () => ({
  listTags: vi.fn(),
}))

import { createTask, deleteTask, listTasks } from '../../src/api/tasks/tasksApi'
import { listTags } from '../../src/api/tags/tagsApi'

describe('ensureGuidedTourDemoTask', () => {
  beforeEach(() => {
    vi.mocked(listTasks).mockReset()
    vi.mocked(createTask).mockReset()
    vi.mocked(deleteTask).mockReset()
    vi.mocked(listTags).mockReset()
  })

  it('reuses existing training task', async () => {
    vi.mocked(listTasks).mockResolvedValue([
      {
        id: 'demo-task',
        title: TOUR_DEMO_TASK_TITLE,
        description: TOUR_DEMO_TASK_DESCRIPTION,
        priority: 'medium',
        due_at: '2030-01-15T00:00:00Z',
        is_tour_demo: true,
        tags: [{ id: 'tag-1', name: 't', color: '#000', slug: 't' }],
      } as never,
    ])
    const result = await ensureGuidedTourDemoTask('me')
    expect(result).toMatchObject({
      ok: true,
      created: false,
      taskId: 'demo-task',
    })
    expect(createTask).not.toHaveBeenCalled()
  })

  it('ignores same title without is_tour_demo', async () => {
    vi.mocked(listTasks).mockResolvedValue([
      {
        id: 'named-like-demo',
        title: TOUR_DEMO_TASK_TITLE,
        is_tour_demo: false,
        tags: [],
      } as never,
    ])
    vi.mocked(listTags).mockResolvedValue([])
    vi.mocked(createTask).mockResolvedValue({ id: 'new-demo' } as never)
    const result = await ensureGuidedTourDemoTask('me')
    expect(result).toMatchObject({ ok: true, created: true, taskId: 'new-demo' })
    expect(createTask).toHaveBeenCalled()
  })

  it('creates training task with fields when missing', async () => {
    vi.mocked(listTasks).mockResolvedValue([])
    vi.mocked(listTags).mockResolvedValue([{ id: 'tag-1', name: 't', color: '#000', slug: 't' } as never])
    vi.mocked(createTask).mockResolvedValue({ id: 'new-demo' } as never)

    const result = await ensureGuidedTourDemoTask('me')
    expect(result).toMatchObject({ ok: true, created: true, taskId: 'new-demo' })
    expect(createTask).toHaveBeenCalledWith(
      expect.objectContaining({
        title: TOUR_DEMO_TASK_TITLE,
        assignee_subs: ['me'],
        priority: 'medium',
        tag_ids: ['tag-1'],
        description: TOUR_DEMO_TASK_DESCRIPTION,
        is_tour_demo: true,
      }),
    )
  })

  it('fails without current user', async () => {
    const result = await ensureGuidedTourDemoTask('')
    expect(result.ok).toBe(false)
    expect(createTask).not.toHaveBeenCalled()
  })

  it('assignee_subs — только текущий user', async () => {
    vi.mocked(listTasks).mockResolvedValue([])
    vi.mocked(listTags).mockResolvedValue([])
    vi.mocked(createTask).mockResolvedValue({ id: 'new-demo' } as never)
    await ensureGuidedTourDemoTask('me')
    const body = vi.mocked(createTask).mock.calls[0]?.[0] as { assignee_subs: string[] }
    expect(body.assignee_subs).toEqual(['me'])
  })

  it('cleanupGuidedTourDemoTask swallows delete errors', async () => {
    vi.mocked(deleteTask).mockRejectedValue(new Error('gone'))
    await expect(cleanupGuidedTourDemoTask('x')).resolves.toBeUndefined()
  })

  it('stepNeedsTourDemoTask detects create-form, field walkthrough and detail section steps', () => {
    expect(stepNeedsTourDemoTask({ id: 'tasks-create-form' })).toBe(true)
    expect(stepNeedsTourDemoTask({ id: 'tasks-create-title' })).toBe(true)
    expect(stepNeedsTourDemoTask({ id: 'tasks-detail-subtasks' })).toBe(true)
    expect(stepNeedsTourDemoTask({ id: 'tasks-detail-files' })).toBe(true)
    expect(stepNeedsTourDemoTask({ id: 'tasks-kanban-card' })).toBe(true)
    expect(stepNeedsTourDemoTask({ id: 'tasks-kanban-column-header' })).toBe(false)
    expect(stepNeedsTourDemoTask({ id: 'tasks-create' })).toBe(false)
  })

  it('buildTourDemoTaskPrefill sets suppressAutoCreate', () => {
    const prefill = buildTourDemoTaskPrefill('me', ['t1'])
    expect(prefill.suppressAutoCreate).toBe(true)
    expect(prefill.assigneeSubs).toEqual(['me'])
    expect(prefill.tagIds).toEqual(['t1'])
  })
})
