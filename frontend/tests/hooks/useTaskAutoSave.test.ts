import { describe, expect, it } from 'vitest'

import {
  buildPatchBody,
  formEqualsServer,
  formStateFromTask,
} from '../../src/hooks/useTaskAutoSave'
import type { PortalTask } from '../../src/types/task'

function minimalTask(overrides: Partial<PortalTask> = {}): PortalTask {
  return {
    id: 'task-1',
    number: 1,
    title: 'Задача',
    description: null,
    status: 'todo',
    priority: 'medium',
    creator_sub: 'user-a',
    assignee_sub: null,
    assignee_subs: [],
    due_at: null,
    document_id: null,
    chat_id: null,
    source_message_id: null,
    parent_task_id: null,
    position: 0,
    version: 1,
    tags: [],
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  }
}

describe('formEqualsServer', () => {
  it('считает пустой HTML и null/пустую строку на сервере одинаковыми', () => {
    const task = minimalTask({ description: null })
    const server = formStateFromTask(task)
    const form = { ...server, description: '<p></p>' }

    expect(formEqualsServer(form, task)).toBe(true)
  })

  it('считает пустой HTML и сохранённое описание разными', () => {
    const task = minimalTask({ description: '<p>Текст</p>' })
    const server = formStateFromTask(task)
    const form = { ...server, description: '<p></p>' }

    expect(formEqualsServer(form, task)).toBe(false)
  })

  it('не считает HTML только с изображением пустым', () => {
    const imageHtml =
      '<figure class="buildin-figure" data-align="center"><img class="buildin-inline-image" src="/api/v1/portal/rich-media/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee/file" alt=""></figure>'
    const task = minimalTask({ description: null })
    const server = formStateFromTask(task)
    const form = { ...server, description: imageHtml }

    expect(formEqualsServer(form, task)).toBe(false)
  })

  it('игнорирует порядок исполнителей при сравнении с сервером', () => {
    const task = minimalTask({
      assignee_subs: ['sub-a', 'sub-b'],
      assignee_sub: 'sub-a',
    })
    const server = formStateFromTask(task)
    const form = { ...server, assigneeSubs: ['sub-b', 'sub-a'] }

    expect(formEqualsServer(form, task)).toBe(true)
  })

  it('считает разный набор исполнителей изменением', () => {
    const task = minimalTask({
      assignee_subs: ['sub-a', 'sub-b'],
      assignee_sub: 'sub-a',
    })
    const server = formStateFromTask(task)
    const form = { ...server, assigneeSubs: ['sub-a'] }

    expect(formEqualsServer(form, task)).toBe(false)
  })

  it('игнорирует порядок тегов', () => {
    const task = minimalTask({
      tags: [
        { id: 't1', name: 'A', slug: 'a', color: '', version: 1 },
        { id: 't2', name: 'B', slug: 'b', color: '', version: 1 },
      ],
    })
    const server = formStateFromTask(task)
    expect(formEqualsServer({ ...server, selectedTagIds: ['t2', 't1'] }, task)).toBe(true)
  })

  it('смена title/status/dueDate — изменение', () => {
    const task = minimalTask()
    const server = formStateFromTask(task)
    expect(formEqualsServer({ ...server, title: 'Другое' }, task)).toBe(false)
    expect(formEqualsServer({ ...server, status: 'done' }, task)).toBe(false)
    expect(formEqualsServer({ ...server, dueDate: '2026-02-01' }, task)).toBe(false)
  })
})

describe('formStateFromTask', () => {
  it('fallback на assignee_sub, если assignee_subs пуст', () => {
    const task = minimalTask({ assignee_sub: 'only', assignee_subs: [] })
    expect(formStateFromTask(task).assigneeSubs).toEqual(['only'])
  })

  it('пустые due_at / document_id → пустые строки формы', () => {
    const state = formStateFromTask(minimalTask({ due_at: null, document_id: null }))
    expect(state.dueDate).toBe('')
    expect(state.documentId).toBe('')
  })
})

describe('buildPatchBody', () => {
  it('возвращает null, если нет dirty-полей', () => {
    const task = minimalTask()
    const form = formStateFromTask(task)
    expect(buildPatchBody(form, task, true)).toBeNull()
  })

  it('при смене title включает expected_version и только dirty-ключи', () => {
    const task = minimalTask({ version: 3 })
    const form = { ...formStateFromTask(task), title: 'Новый заголовок' }
    expect(buildPatchBody(form, task, true)).toEqual({
      expected_version: 3,
      title: 'Новый заголовок',
    })
  })
})
