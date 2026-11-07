import { describe, expect, it } from 'vitest'

import { partitionParentSubtasks } from '../../../src/domain/tasks/taskBoardPref'
import type { PortalTask } from '../../../src/types/task'

function subtask(id: string, status: string, position = 0): PortalTask {
  return {
    id,
    number: null,
    title: id,
    description: null,
    creator_sub: 'u',
    assignee_sub: null,
    assignee_subs: [],
    status,
    priority: 'medium',
    due_at: null,
    document_id: null,
    chat_id: null,
    source_message_id: null,
    parent_task_id: 'parent',
    position,
    version: 1,
    created_at: '',
    updated_at: '',
    tags: [],
  }
}

describe('partitionParentSubtasks', () => {
  it('делит детей на same-column и other', () => {
    const children = [
      subtask('a', 'todo', 0),
      subtask('b', 'done', 1),
      subtask('c', 'todo', 2),
    ]
    const { inColumn, otherColumns } = partitionParentSubtasks(children, 'todo')
    expect(inColumn.map((t) => t.id)).toEqual(['a', 'c'])
    expect(otherColumns.map((t) => t.id)).toEqual(['b'])
  })

  it('при пустом списке детей оба массива пустые', () => {
    expect(partitionParentSubtasks([], 'todo')).toEqual({ inColumn: [], otherColumns: [] })
  })

  it('если все дети в другой колонке — inColumn пуст, other полный', () => {
    const children = [subtask('x', 'done'), subtask('y', 'in_progress')]
    const { inColumn, otherColumns } = partitionParentSubtasks(children, 'todo')
    expect(inColumn).toEqual([])
    expect(otherColumns.map((t) => t.id)).toEqual(['x', 'y'])
  })
})
