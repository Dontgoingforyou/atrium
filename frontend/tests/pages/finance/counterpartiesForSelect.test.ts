import { describe, expect, it } from 'vitest'
import { counterpartiesForSelect } from '../../../src/pages/finance/counterpartiesForSelect'
import type { PortalCounterparty } from '../../../src/types/finance'

function cp(id: string, isActive: boolean): PortalCounterparty {
  return {
    id,
    name: id,
    inn: null,
    contact_email: null,
    contact_phone: null,
    counterparty_type: 'vendor',
    note: null,
    is_active: isActive,
    author_sub: 'u',
    created_at: '',
    updated_at: '',
  }
}

describe('counterpartiesForSelect', () => {
  it('возвращает пустой список для undefined', () => {
    expect(counterpartiesForSelect(undefined, 'x')).toEqual([])
  })

  it('оставляет только активных, если keepId не задан', () => {
    const list = [cp('a', true), cp('b', false)]
    expect(counterpartiesForSelect(list, null).map((c) => c.id)).toEqual(['a'])
  })

  it('включает неактивного с keepId при редактировании', () => {
    const list = [cp('a', true), cp('b', false)]
    expect(counterpartiesForSelect(list, 'b').map((c) => c.id)).toEqual(['a', 'b'])
  })
})
