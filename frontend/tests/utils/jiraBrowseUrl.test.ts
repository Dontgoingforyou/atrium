import { describe, expect, it } from 'vitest'

import { jiraBrowseUrl } from '../../src/utils/jiraBrowseUrl'

describe('jiraBrowseUrl', () => {
  it('собирает browse URL с дефолтным base', () => {
    expect(jiraBrowseUrl('AUSPACE-270')).toBe(
      'https://jira.example.com/browse/AUSPACE-270',
    )
  })

  it('кодирует опасные символы в ключе', () => {
    expect(jiraBrowseUrl('../evil')).toBe(
      'https://jira.example.com/browse/..%2Fevil',
    )
    expect(jiraBrowseUrl('AUSPACE-270?x=1')).toBe(
      'https://jira.example.com/browse/AUSPACE-270%3Fx%3D1',
    )
  })
})
