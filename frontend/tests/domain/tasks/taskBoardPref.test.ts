import { describe, expect, it } from 'vitest'
import type { PortalTask, PortalTaskColumn } from '../../../src/types/task'
import { computeKanbanDisplay } from '../../../src/domain/tasks/taskBoardPref'
import { KANBAN_OTHER_BUCKET } from '../../../src/domain/kanban/kanbanDisplayCommon'

const cols: PortalTaskColumn[] = [
  {
    id: '1',
    title: 'A',
    color: '#111',
    status_key: 'todo',
    position: 0,
    exclude_from_kpi: false,
  },
  {
    id: '2',
    title: 'B',
    color: '#222',
    status_key: 'done',
    position: 1,
    exclude_from_kpi: true,
  },
  {
    id: '3',
    title: 'C',
    color: '#333',
    status_key: 'cancelled',
    position: 2,
    exclude_from_kpi: true,
  },
]

function task(id: string, status: string, parentId: string | null = null): PortalTask {
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
    parent_task_id: parentId,
    position: 0,
    version: 1,
    created_at: '',
    updated_at: '',
    tags: [],
  }
}

describe('computeKanbanDisplay', () => {
  it('скрытая колонка не попадает на доску и не создаёт «Прочие»', () => {
    const tasks = [task('t1', 'cancelled'), task('t2', 'todo')]
    const pref = {
      column_order: ['todo', 'done', 'cancelled'],
      hidden_status_keys: ['cancelled'],
      title_overrides: {},
    }
    const d = computeKanbanDisplay(cols, pref, tasks, false)
    expect(d.statusOrder).not.toContain(KANBAN_OTHER_BUCKET)
    expect(d.statusOrder).not.toContain('cancelled')
    expect(d.statusOrder).toContain('todo')
    expect(d.tasksForStatus(KANBAN_OTHER_BUCKET)).toEqual([])
    expect(d.tasksForStatus('todo').map((t) => t.id)).toEqual(['t2'])
  })

  it('при «Показать скрытые» колонка и задачи на своём месте', () => {
    const tasks = [task('t1', 'cancelled')]
    const pref = {
      column_order: [],
      hidden_status_keys: ['cancelled'],
      title_overrides: {},
    }
    const d = computeKanbanDisplay(cols, pref, tasks, true)
    expect(d.statusOrder).not.toContain(KANBAN_OTHER_BUCKET)
    expect(d.statusOrder).toContain('cancelled')
    expect(d.tasksForStatus('cancelled').map((t) => t.id)).toEqual(['t1'])
  })

  it('после снятия скрытия колонка и задачи снова на доске', () => {
    const tasks = [task('t1', 'cancelled')]
    const hiddenPref = {
      column_order: ['todo', 'done', 'cancelled'],
      hidden_status_keys: ['cancelled'],
      title_overrides: {},
    }
    const shownPref = { ...hiddenPref, hidden_status_keys: [] }
    const hidden = computeKanbanDisplay(cols, hiddenPref, tasks, false)
    const shown = computeKanbanDisplay(cols, shownPref, tasks, false)
    expect(hidden.statusOrder).not.toContain('cancelled')
    expect(shown.statusOrder).toContain('cancelled')
    expect(shown.tasksForStatus('cancelled').map((t) => t.id)).toEqual(['t1'])
  })

  it('подзадача с другим статусом, чем родитель, попадает в колонку своего статуса', () => {
    const tasks = [task('parent', 'todo'), task('child', 'done', 'parent')]
    const pref = {
      column_order: ['todo', 'done', 'cancelled'],
      hidden_status_keys: [],
      title_overrides: {},
    }
    const d = computeKanbanDisplay(cols, pref, tasks, false)
    expect(d.tasksForStatus('todo').map((t) => t.id)).toEqual(['parent'])
    expect(d.tasksForStatus('done').map((t) => t.id)).toEqual(['child'])
  })

  it('hide_subtasks — только родительские задачи, подзадачи скрыты', () => {
    const tasks = [task('parent', 'todo'), task('child', 'todo', 'parent'), task('alone', 'done', 'parent')]
    const pref = {
      column_order: ['todo', 'done', 'cancelled'],
      hidden_status_keys: [],
      title_overrides: {},
      hide_subtasks: true,
    }
    const d = computeKanbanDisplay(cols, pref, tasks, false)
    expect(d.hideSubtasks).toBe(true)
    expect(d.subtasksFlat).toBe(false)
    expect(d.tasksForStatus('todo').map((t) => t.id)).toEqual(['parent'])
    expect(d.tasksForStatus('done').map((t) => t.id)).toEqual([])
  })
})
