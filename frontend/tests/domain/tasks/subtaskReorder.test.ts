import { describe, expect, it } from 'vitest'

import { resolveSubtaskReorderAnchor } from '../../../src/domain/tasks/subtaskReorder'
import type { PortalTask } from '../../../src/types/task'

function task(partial: Pick<PortalTask, 'id' | 'status'>): PortalTask {
  return {
    id: partial.id,
    number: null,
    title: partial.id,
    description: null,
    creator_sub: 'u',
    assignee_sub: null,
    assignee_subs: [],
    status: partial.status,
    priority: 'medium',
    due_at: null,
    document_id: null,
    chat_id: null,
    source_message_id: null,
    parent_task_id: null,
    position: 0,
    version: 1,
    created_at: '',
    updated_at: '',
    tags: [],
  }
}

describe('resolveSubtaskReorderAnchor', () => {
  it('для первого в списке ставит before следующего', () => {
    const ordered = [task({ id: 'a', status: 'todo' }), task({ id: 'b', status: 'todo' })]
    expect(resolveSubtaskReorderAnchor(ordered, 'a')).toEqual({
      status: 'todo',
      afterTaskId: null,
      beforeTaskId: 'b',
    })
  })

  it('для не-первого ставит after предыдущего', () => {
    const ordered = [task({ id: 'a', status: 'todo' }), task({ id: 'b', status: 'todo' })]
    expect(resolveSubtaskReorderAnchor(ordered, 'b')).toEqual({
      status: 'todo',
      afterTaskId: 'a',
      beforeTaskId: null,
    })
  })

  it('якорь — сосед в полном списке, статус перетаскиваемой не меняет', () => {
    const ordered = [
      task({ id: 'a', status: 'todo' }),
      task({ id: 'x', status: 'done' }),
      task({ id: 'b', status: 'todo' }),
    ]
    expect(resolveSubtaskReorderAnchor(ordered, 'b')).toEqual({
      status: 'todo',
      afterTaskId: 'x',
      beforeTaskId: null,
    })
  })

  it('возвращает null если id нет в списке', () => {
    expect(resolveSubtaskReorderAnchor([task({ id: 'a', status: 'todo' })], 'missing')).toBeNull()
  })
})
