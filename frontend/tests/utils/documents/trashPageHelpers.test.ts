import { describe, expect, it, vi, afterEach } from 'vitest'

import { daysUntil, removeTrashItem, type TrashPageData } from '@/utils/documents/trashPageHelpers'
import type { PortalDocumentTrashItem } from '@/types/document'

function item(id: string): PortalDocumentTrashItem {
  return {
    id,
    title: `Doc ${id}`,
    deleted_at: '2026-01-01T00:00:00Z',
    auto_purge_at: '2026-04-01T00:00:00Z',
    deleted_by_sub: null,
    deleted_by_display_name: null,
    deleted_by_email: null,
  }
}

describe('daysUntil', () => {
  afterEach(() => {
    vi.useRealTimers()
  })

  it('считает целые сутки до даты', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-03-30T12:00:00Z'))
    expect(daysUntil('2026-04-01T12:00:00Z')).toBe(2)
  })

  it('не уходит в минус для прошедшей даты', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-05-01T00:00:00Z'))
    expect(daysUntil('2026-04-01T00:00:00Z')).toBe(0)
  })

  it('битая дата → 0, не NaN', () => {
    expect(daysUntil('not-a-date')).toBe(0)
    expect(daysUntil('')).toBe(0)
  })
})

describe('removeTrashItem', () => {
  it('удаляет строку и уменьшает total', () => {
    const data: TrashPageData = {
      items: [item('a'), item('b')],
      total: 2,
      skip: 0,
      limit: 50,
    }
    expect(removeTrashItem(data, 'a')?.items.map((r) => r.id)).toEqual(['b'])
    expect(removeTrashItem(data, 'a')?.total).toBe(1)
  })

  it('не меняет объект, если id нет', () => {
    const data: TrashPageData = {
      items: [item('a')],
      total: 1,
      skip: 0,
      limit: 50,
    }
    expect(removeTrashItem(data, 'missing')).toBe(data)
  })

  it('undefined → undefined', () => {
    expect(removeTrashItem(undefined, 'a')).toBeUndefined()
  })
})
