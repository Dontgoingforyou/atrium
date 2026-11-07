import { describe, expect, it } from 'vitest'

import { buildPlaceholderEntry } from '../../src/hooks/useSpecialistBoardUndo'

describe('buildPlaceholderEntry', () => {
  it('собирает optimistic-плейсхолдер с временным id и переданными специалистом/менеджером/колонкой', () => {
    const placeholder = buildPlaceholderEntry({
      specialistSub: 'spec-1',
      managerSub: 'mgr-1',
      columnKey: 'interview',
    })

    expect(placeholder.id).toMatch(/^pending-/)
    expect(placeholder.specialist_sub).toBe('spec-1')
    expect(placeholder.manager_sub).toBe('mgr-1')
    expect(placeholder.column_key).toBe('interview')
    expect(placeholder.position).toBe(0)
    expect(placeholder.display_name).toBeNull()
    expect(placeholder.email).toBeNull()
    expect(placeholder.avatar_url).toBeNull()
    expect(placeholder.status_id).toBeNull()
  })

  it('подставляет известный профиль специалиста (specialist hint), если он передан', () => {
    const placeholder = buildPlaceholderEntry({
      specialistSub: 'spec-1',
      managerSub: 'mgr-1',
      columnKey: 'interview',
      specialist: { display_name: 'Иван Иванов', email: 'ivan@example.com', avatar_url: null },
    })

    expect(placeholder.display_name).toBe('Иван Иванов')
    expect(placeholder.email).toBe('ivan@example.com')
  })

  it('каждый вызов создаёт уникальный id — плейсхолдеры не конфликтуют между собой', () => {
    const a = buildPlaceholderEntry({ specialistSub: 's', managerSub: 'm1', columnKey: 'c' })
    const b = buildPlaceholderEntry({ specialistSub: 's', managerSub: 'm2', columnKey: 'c' })

    expect(a.id).not.toBe(b.id)
  })
})
