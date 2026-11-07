import { describe, expect, it } from 'vitest'

import { userCanChangeTaskAssignees, userCanDeleteTask, userCanEditTask } from '../../../src/domain/tasks/taskPermissions'
import type { PortalTask } from '../../../src/types/task'

const baseTask = {
  creator_sub: 'creator',
  assignee_sub: 'assignee',
  assignee_subs: ['assignee'],
} as Pick<PortalTask, 'creator_sub' | 'assignee_sub' | 'assignee_subs'>

describe('userCanEditTask', () => {
  it('allows creator', () => {
    expect(userCanEditTask(baseTask, 'creator')).toBe(true)
  })

  it('allows assignee who is not creator', () => {
    expect(userCanEditTask(baseTask, 'assignee')).toBe(true)
  })

  it('allows additional assignee from assignee_subs', () => {
    const task = {
      creator_sub: 'creator',
      assignee_sub: 'assignee',
      assignee_subs: ['assignee', 'co-worker'],
    } as Pick<PortalTask, 'creator_sub' | 'assignee_sub' | 'assignee_subs'>
    expect(userCanEditTask(task, 'co-worker')).toBe(true)
  })

  it('allows portal admin for any task', () => {
    expect(userCanEditTask(baseTask, 'admin', true)).toBe(true)
  })

  it('denies user who is neither creator nor assignee', () => {
    expect(userCanEditTask(baseTask, 'admin')).toBe(false)
    expect(userCanEditTask(baseTask, 'bystander')).toBe(false)
  })

  it('primary assignee при assignee_subs=undefined — edit true', () => {
    const task = {
      creator_sub: 'creator',
      assignee_sub: 'assignee',
      assignee_subs: undefined,
    }
    expect(userCanEditTask(task, 'assignee')).toBe(true)
  })

  it('чужой при assignee_subs=undefined/null — edit false', () => {
    const task = {
      creator_sub: 'creator',
      assignee_sub: 'assignee',
      assignee_subs: undefined,
    }
    expect(userCanEditTask(task, 'co-worker')).toBe(false)
    expect(
      userCanEditTask(
        { creator_sub: 'creator', assignee_sub: 'assignee', assignee_subs: null },
        'co-worker',
      ),
    ).toBe(false)
  })
})

describe('userCanChangeTaskAssignees', () => {
  it('allows creator', () => {
    expect(userCanChangeTaskAssignees(baseTask, 'creator')).toBe(true)
  })

  it('allows portal admin', () => {
    expect(userCanChangeTaskAssignees(baseTask, 'admin', true)).toBe(true)
  })

  it('denies non-creator without admin', () => {
    expect(userCanChangeTaskAssignees(baseTask, 'assignee')).toBe(false)
    expect(userCanChangeTaskAssignees(baseTask, 'admin')).toBe(false)
  })
})

describe('userCanDeleteTask', () => {
  it('allows portal admin', () => {
    expect(userCanDeleteTask({ creator_sub: 'creator', is_tour_demo: false }, 'admin', true)).toBe(
      true,
    )
  })

  it('allows creator of tour demo task', () => {
    expect(userCanDeleteTask({ creator_sub: 'me', is_tour_demo: true }, 'me')).toBe(true)
  })

  it('denies creator without is_tour_demo even with tour title', () => {
    expect(userCanDeleteTask({ creator_sub: 'me', is_tour_demo: false }, 'me')).toBe(false)
  })

  it('allows manager creator of regular task', () => {
    expect(userCanDeleteTask({ creator_sub: 'me', is_tour_demo: false }, 'me', false, true)).toBe(
      true,
    )
  })

  it('denies manager of foreign regular task', () => {
    expect(userCanDeleteTask({ creator_sub: 'other', is_tour_demo: false }, 'me', false, true)).toBe(
      false,
    )
  })

  it('denies non-manager creator of regular task', () => {
    expect(userCanDeleteTask({ creator_sub: 'me', is_tour_demo: false }, 'me', false, false)).toBe(
      false,
    )
  })

  it('denies non-creator of tour demo', () => {
    expect(userCanDeleteTask({ creator_sub: 'me', is_tour_demo: true }, 'other')).toBe(false)
  })

  it('denies creator при is_tour_demo=undefined', () => {
    expect(userCanDeleteTask({ creator_sub: 'me' }, 'me')).toBe(false)
  })

  it('assignee ≠ creator: edit yes, changeAssignees/delete no', () => {
    expect(userCanEditTask(baseTask, 'assignee')).toBe(true)
    expect(userCanChangeTaskAssignees(baseTask, 'assignee')).toBe(false)
    expect(
      userCanDeleteTask({ creator_sub: 'creator', is_tour_demo: true }, 'assignee'),
    ).toBe(false)
  })
})
