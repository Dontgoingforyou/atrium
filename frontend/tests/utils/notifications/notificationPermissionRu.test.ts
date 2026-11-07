import { describe, expect, it } from 'vitest'

import { notificationPermissionLabelRu } from '@/utils/notifications/notificationPermissionRu'

describe('notificationPermissionLabelRu', () => {
  it('переводит известные значения', () => {
    expect(notificationPermissionLabelRu('granted')).toBe('разрешено')
    expect(notificationPermissionLabelRu('denied')).toBe('запрещено')
    expect(notificationPermissionLabelRu('default')).toBe('не запрошено')
  })
})
