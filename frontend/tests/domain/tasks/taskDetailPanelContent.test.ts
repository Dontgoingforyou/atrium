// @vitest-environment jsdom

import { describe, expect, it } from 'vitest'

import {
  countCommentsPanelContent,
  countLinksPanelContent,
  panelContentCountWhenLoaded,
  resolveManualOrAutoOpen,
} from '../../../src/domain/tasks/taskDetailPanelContent'
import type { ThreadComment } from '../../../src/types/commentThread'

function comment(partial: Partial<ThreadComment> & Pick<ThreadComment, 'id' | 'body'>): ThreadComment {
  return {
    parent_id: null,
    author_sub: 'u',
    mentions: [],
    version: 1,
    created_at: '',
    updated_at: '',
    replies: [],
    ...partial,
  }
}

describe('resolveManualOrAutoOpen', () => {
  it('без ручного выбора — открыта, если есть содержимое', () => {
    expect(resolveManualOrAutoOpen(null, true)).toBe(true)
  })

  it('без ручного выбора — закрыта, если содержимого нет', () => {
    expect(resolveManualOrAutoOpen(null, false)).toBe(false)
  })

  it('ручной выбор «раскрыть» перекрывает отсутствие данных', () => {
    expect(resolveManualOrAutoOpen(true, false)).toBe(true)
  })

  it('ручной выбор «свернуть» перекрывает наличие данных', () => {
    expect(resolveManualOrAutoOpen(false, true)).toBe(false)
  })
})

describe('panelContentCountWhenLoaded', () => {
  it('до успеха — undefined', () => {
    expect(panelContentCountWhenLoaded(false, 5)).toBeUndefined()
  })

  it('после успеха — count или 0', () => {
    expect(panelContentCountWhenLoaded(true, 3)).toBe(3)
    expect(panelContentCountWhenLoaded(true, undefined)).toBe(0)
  })
})

describe('countLinksPanelContent', () => {
  it('родитель без документа — больше нуля', () => {
    expect(
      countLinksPanelContent({
        hasDocument: false,
        hasParent: true,
        subtasksLoaded: false,
        subtaskCount: 0,
      }),
    ).toBe(1)
  })

  it('только подзадачи — больше нуля', () => {
    expect(
      countLinksPanelContent({
        hasDocument: false,
        hasParent: false,
        subtasksLoaded: true,
        subtaskCount: 2,
      }),
    ).toBe(2)
  })

  it('пустой блок — ноль', () => {
    expect(
      countLinksPanelContent({
        hasDocument: false,
        hasParent: false,
        subtasksLoaded: true,
        subtaskCount: 0,
      }),
    ).toBe(0)
  })

  it('незагруженные подзадачи без документа и родителя — undefined', () => {
    expect(
      countLinksPanelContent({
        hasDocument: false,
        hasParent: false,
        subtasksLoaded: false,
        subtaskCount: 0,
      }),
    ).toBeUndefined()
  })
})

describe('countCommentsPanelContent', () => {
  it('пусто / undefined → 0', () => {
    expect(countCommentsPanelContent(undefined)).toBe(0)
    expect(countCommentsPanelContent([])).toBe(0)
  })

  it('считает комментарии с текстом или media, включая replies', () => {
    const tree = [
      comment({
        id: '1',
        body: '  ',
        replies: [
          comment({ id: '1a', body: 'reply' }),
          comment({
            id: '1b',
            body: '',
            media: [
              {
                id: 'm1',
                content_type: 'image/png',
                original_filename: 'a.png',
                file_size: 1,
                download_url: '/',
                file_path: 'a',
                created_at: '',
              },
            ],
          }),
        ],
      }),
      comment({ id: '2', body: '' }),
    ]
    expect(countCommentsPanelContent(tree)).toBe(2)
  })
})
