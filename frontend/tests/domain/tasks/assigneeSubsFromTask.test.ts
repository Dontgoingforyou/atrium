import { describe, expect, it } from 'vitest'

import { assigneeSubsFromTask } from '@/domain/tasks/assigneeSubsFromTask'

describe('assigneeSubsFromTask', () => {
  it('возвращает всех исполнителей, не только первого', () => {
    expect(
      assigneeSubsFromTask({
        assignee_sub: 'kseniya',
        assignee_subs: ['kseniya', 'diana'],
      }),
    ).toEqual(['kseniya', 'diana'])
  })

  it('fallback на assignee_sub, если список пуст', () => {
    expect(assigneeSubsFromTask({ assignee_sub: 'only', assignee_subs: [] })).toEqual(['only'])
  })

  it('пустой список, если исполнителей нет', () => {
    expect(assigneeSubsFromTask({ assignee_sub: null, assignee_subs: [] })).toEqual([])
    expect(assigneeSubsFromTask({})).toEqual([])
  })
})
