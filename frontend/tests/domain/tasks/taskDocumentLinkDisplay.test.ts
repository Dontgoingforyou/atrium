import { describe, expect, it } from 'vitest'
import { resolveTaskLinkedDocumentTitle } from '../../../src/domain/tasks/taskDocumentLinkDisplay'

describe('resolveTaskLinkedDocumentTitle', () => {
  it('не показывает устаревший title при смене document_id', () => {
    const result = resolveTaskLinkedDocumentTitle(
      'doc-new',
      {
        data: { id: 'doc-old', title: 'Старый документ' },
        isPending: false,
        isFetching: true,
      },
      'Новый из задачи',
    )
    expect(result).toEqual({ title: 'Новый из задачи', isLoading: true })
  })

  it('берёт title из query когда id совпадает', () => {
    const result = resolveTaskLinkedDocumentTitle(
      'doc-1',
      {
        data: { id: 'doc-1', title: 'Актуальный' },
        isPending: false,
        isFetching: false,
      },
      'Устаревший из задачи',
    )
    expect(result).toEqual({ title: 'Актуальный', isLoading: false })
  })

  it('показывает загрузку без embedded title', () => {
    const result = resolveTaskLinkedDocumentTitle(
      'doc-1',
      { data: undefined, isPending: true, isFetching: true },
      null,
    )
    expect(result).toEqual({ title: '', isLoading: true })
  })
})
