import { describe, expect, it } from 'vitest'

import {
  parseManagerSubsFromSearchParams,
  parseSpecialistScopeFromUrl,
  parseSpecialistSubsFromSearchParams,
  parseSpecialistViewFromUrl,
} from '../../../src/pages/specialists/specialistsPageUrl'

describe('specialistsPageUrl filters', () => {
  it('парсит manager_sub из URL', () => {
    const p = new URLSearchParams('manager_sub=a&manager_sub=b')
    expect(parseManagerSubsFromSearchParams(p)).toEqual(['a', 'b'])
  })

  it('парсит specialist_sub из URL', () => {
    const p = new URLSearchParams('specialist_sub=s1')
    expect(parseSpecialistSubsFromSearchParams(p)).toEqual(['s1'])
  })
})

describe('specialistsPageUrl scope/view', () => {
  it('scope: all только при явном параметре, иначе my', () => {
    expect(parseSpecialistScopeFromUrl('all')).toBe('all')
    expect(parseSpecialistScopeFromUrl(null)).toBe('my')
    expect(parseSpecialistScopeFromUrl('my')).toBe('my')
    expect(parseSpecialistScopeFromUrl('team')).toBe('my')
    expect(parseSpecialistScopeFromUrl('')).toBe('my')
  })

  it('view: list только при явном параметре, иначе kanban', () => {
    expect(parseSpecialistViewFromUrl('list')).toBe('list')
    expect(parseSpecialistViewFromUrl(null)).toBe('kanban')
    expect(parseSpecialistViewFromUrl('kanban')).toBe('kanban')
    expect(parseSpecialistViewFromUrl('BOARD')).toBe('kanban')
  })

  it('пустой manager_sub → []', () => {
    expect(parseManagerSubsFromSearchParams(new URLSearchParams('manager_sub='))).toEqual([])
  })
})
