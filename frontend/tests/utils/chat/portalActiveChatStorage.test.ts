// @vitest-environment jsdom

import { afterEach, describe, expect, it } from 'vitest'

import {
  readPortalFocusedChatIds,
  setPortalActiveChatOnChatsPage,
  setPortalActiveChatOnFloatingWidget,
} from '../../../src/utils/chat/portalActiveChatStorage'

afterEach(() => {
  sessionStorage.clear()
})

describe('portalActiveChatStorage', () => {
  it('пишет и читает chats page / widget', () => {
    setPortalActiveChatOnChatsPage('c1')
    setPortalActiveChatOnFloatingWidget('c2')
    expect(readPortalFocusedChatIds()).toEqual({ chatsPage: 'c1', widget: 'c2' })
  })

  it('null снимает ключ', () => {
    setPortalActiveChatOnChatsPage('c1')
    setPortalActiveChatOnChatsPage(null)
    setPortalActiveChatOnFloatingWidget('c2')
    setPortalActiveChatOnFloatingWidget(null)
    expect(readPortalFocusedChatIds()).toEqual({ chatsPage: null, widget: null })
  })
})
