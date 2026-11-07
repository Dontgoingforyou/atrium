// @vitest-environment jsdom

import { afterEach, describe, expect, it } from 'vitest'

import {
  readFloatingDmWidgetSession,
  writeFloatingDmWidgetSession,
} from '../../../src/utils/chat/floatingDmWidgetSession'

afterEach(() => {
  sessionStorage.clear()
})

describe('floatingDmWidgetSession', () => {
  it('round-trips view and activeChatId', () => {
    writeFloatingDmWidgetSession({ view: 'chat', activeChatId: 'chat-1' })
    expect(readFloatingDmWidgetSession()).toEqual({ view: 'chat', activeChatId: 'chat-1' })
  })

  it('clears session when null', () => {
    writeFloatingDmWidgetSession({ view: 'list', activeChatId: null })
    writeFloatingDmWidgetSession(null)
    expect(readFloatingDmWidgetSession()).toBeNull()
  })

  it('битый JSON / неизвестный view → null', () => {
    sessionStorage.setItem('portal_floating_dm_widget_v1', '{not-json')
    expect(readFloatingDmWidgetSession()).toBeNull()
    sessionStorage.setItem(
      'portal_floating_dm_widget_v1',
      JSON.stringify({ view: 'evil', activeChatId: 'x' }),
    )
    expect(readFloatingDmWidgetSession()).toBeNull()
  })
})
