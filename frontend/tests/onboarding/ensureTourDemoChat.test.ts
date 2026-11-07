import { describe, expect, it, vi, beforeEach } from 'vitest'

import {
  ensureGuidedTourDemoChat,
  findTourDemoEmojiIndex,
  findTourDemoTextIndex,
  resetTourDemoChatSeed,
  stepNeedsTourChatHref,
  stepNeedsTourChatRow,
  stepNeedsTourChatSeed,
  TOUR_DEMO_CHAT_TITLE,
  TOUR_DEMO_EMOJI_BODY,
  TOUR_DEMO_MESSAGE_BODY,
} from '../../src/onboarding/ensureTourDemoChat'
import { tourAnchorSelector } from '../../src/domain/onboarding/guidedTour'

vi.mock('../../src/api/chat/chatApi', () => ({
  listChats: vi.fn(),
  listMessages: vi.fn(),
  createChat: vi.fn(),
  postMessage: vi.fn(),
}))

import {
  createChat,
  listChats,
  listMessages,
  postMessage,
} from '../../src/api/chat/chatApi'

describe('ensureGuidedTourDemoChat', () => {
  beforeEach(() => {
    resetTourDemoChatSeed()
    vi.mocked(listChats).mockReset()
    vi.mocked(listMessages).mockReset()
    vi.mocked(createChat).mockReset()
    vi.mocked(postMessage).mockReset()
  })

  it('reuses existing training chat and skips posts if text and emoji present', async () => {
    vi.mocked(listChats).mockResolvedValue([
      { id: 'demo', title: TOUR_DEMO_CHAT_TITLE, is_direct: false } as never,
    ])
    vi.mocked(listMessages).mockResolvedValue([
      { id: 'm1', body: TOUR_DEMO_MESSAGE_BODY } as never,
      { id: 'm2', body: TOUR_DEMO_EMOJI_BODY } as never,
    ])
    const result = await ensureGuidedTourDemoChat('me')
    expect(result).toEqual({
      ok: true,
      created: false,
      chatId: 'demo',
      messageEnsured: false,
    })
    expect(createChat).not.toHaveBeenCalled()
    expect(postMessage).not.toHaveBeenCalled()
  })

  it('posts tour text and emoji when chat already has other messages', async () => {
    vi.mocked(listChats).mockResolvedValue([
      { id: 'demo', title: TOUR_DEMO_CHAT_TITLE, is_direct: false } as never,
    ])
    vi.mocked(listMessages).mockResolvedValue([
      { id: 'old1', body: 'привет' } as never,
      { id: 'old2', body: '🔥' } as never,
      { id: 'old3', body: 'ещё одно' } as never,
    ])
    vi.mocked(postMessage).mockResolvedValue({} as never)
    const result = await ensureGuidedTourDemoChat('me')
    expect(result).toEqual({
      ok: true,
      created: false,
      chatId: 'demo',
      messageEnsured: true,
    })
    expect(postMessage).toHaveBeenNthCalledWith(1, 'demo', { body: TOUR_DEMO_MESSAGE_BODY })
    expect(postMessage).toHaveBeenNthCalledWith(2, 'demo', { body: TOUR_DEMO_EMOJI_BODY })
  })

  it('adds emoji message when training chat has only text', async () => {
    vi.mocked(listChats).mockResolvedValue([
      { id: 'demo', title: TOUR_DEMO_CHAT_TITLE, is_direct: false } as never,
    ])
    vi.mocked(listMessages).mockResolvedValue([
      { id: 'm1', body: TOUR_DEMO_MESSAGE_BODY } as never,
    ])
    vi.mocked(postMessage).mockResolvedValue({} as never)
    const result = await ensureGuidedTourDemoChat('me')
    expect(result).toEqual({
      ok: true,
      created: false,
      chatId: 'demo',
      messageEnsured: true,
    })
    expect(postMessage).toHaveBeenCalledWith('demo', { body: TOUR_DEMO_EMOJI_BODY })
  })

  it('posts text and emoji into existing empty training chat', async () => {
    vi.mocked(listChats).mockResolvedValue([
      { id: 'demo', title: TOUR_DEMO_CHAT_TITLE, is_direct: false } as never,
      { id: 'other', title: 'GS test', is_direct: false } as never,
    ])
    vi.mocked(listMessages).mockResolvedValue([])
    vi.mocked(postMessage).mockResolvedValue({} as never)
    const result = await ensureGuidedTourDemoChat('me')
    expect(result).toEqual({
      ok: true,
      created: false,
      chatId: 'demo',
      messageEnsured: true,
    })
    expect(postMessage).toHaveBeenNthCalledWith(1, 'demo', { body: TOUR_DEMO_MESSAGE_BODY })
    expect(postMessage).toHaveBeenNthCalledWith(2, 'demo', { body: TOUR_DEMO_EMOJI_BODY })
  })

  it('creates training self-chat when missing', async () => {
    vi.mocked(listChats).mockResolvedValue([{ id: 'gs', title: 'GS test', is_direct: false } as never])
    vi.mocked(createChat).mockResolvedValue({
      id: 'demo',
      title: TOUR_DEMO_CHAT_TITLE,
      is_direct: false,
    } as never)
    vi.mocked(listMessages).mockResolvedValue([])
    vi.mocked(postMessage).mockResolvedValue({} as never)

    const result = await ensureGuidedTourDemoChat('me')
    expect(result).toEqual({
      ok: true,
      created: true,
      chatId: 'demo',
      messageEnsured: true,
    })
    expect(createChat).toHaveBeenCalledWith({
      title: TOUR_DEMO_CHAT_TITLE,
      member_subs: ['me'],
    })
    const createArg = vi.mocked(createChat).mock.calls[0]?.[0] as { member_subs: string[] }
    expect(createArg.member_subs).toEqual(['me'])
    expect(createArg.member_subs).toHaveLength(1)
    expect(createArg.member_subs).not.toContain('other-user')
  })

  it('createChat — только текущий user, без чужих member_subs', async () => {
    vi.mocked(listChats).mockResolvedValue([])
    vi.mocked(createChat).mockResolvedValue({
      id: 'demo',
      title: TOUR_DEMO_CHAT_TITLE,
      is_direct: false,
    } as never)
    vi.mocked(listMessages).mockResolvedValue([
      { id: 'm1', body: TOUR_DEMO_MESSAGE_BODY } as never,
      { id: 'm2', body: TOUR_DEMO_EMOJI_BODY } as never,
    ])
    await ensureGuidedTourDemoChat('self-only')
    expect(createChat).toHaveBeenCalledTimes(1)
    expect(vi.mocked(createChat).mock.calls[0]?.[0]).toEqual({
      title: TOUR_DEMO_CHAT_TITLE,
      member_subs: ['self-only'],
    })
  })

  it('findTourDemoMessageIndexes pick exact training bodies, not later chatter', () => {
    const messages = [
      { id: 'a', body: 'старое' },
      { id: 't', body: TOUR_DEMO_MESSAGE_BODY },
      { id: 'e', body: TOUR_DEMO_EMOJI_BODY },
      { id: 'x', body: '🔥' },
      { id: 'z', body: 'новое' },
    ]
    expect(findTourDemoTextIndex(messages)).toBe(1)
    expect(findTourDemoEmojiIndex(messages)).toBe(2)
  })

  it('skips list and create when demoChatId is already cached', async () => {
    const result = await ensureGuidedTourDemoChat('me', 'cached-demo')
    expect(result).toEqual({
      ok: true,
      created: false,
      chatId: 'cached-demo',
      messageEnsured: false,
    })
    expect(listChats).not.toHaveBeenCalled()
    expect(createChat).not.toHaveBeenCalled()
    expect(listMessages).not.toHaveBeenCalled()
  })

  it('reuses in-flight seed so a second call does not list chats again', async () => {
    vi.mocked(listChats).mockResolvedValue([
      { id: 'demo', title: TOUR_DEMO_CHAT_TITLE, is_direct: false } as never,
    ])
    vi.mocked(listMessages).mockResolvedValue([
      { id: 'm1', body: TOUR_DEMO_MESSAGE_BODY } as never,
      { id: 'm2', body: TOUR_DEMO_EMOJI_BODY } as never,
    ])
    const first = await ensureGuidedTourDemoChat('me')
    const second = await ensureGuidedTourDemoChat('me')
    expect(first.ok).toBe(true)
    expect(second).toEqual(first)
    expect(listChats).toHaveBeenCalledTimes(1)
  })

  it('stepNeedsTourChatRow detects chat-row steps', () => {
    const row = tourAnchorSelector('chats-row')
    expect(stepNeedsTourChatRow({ selector: row })).toBe(true)
    expect(stepNeedsTourChatRow({ openFromSelector: row })).toBe(true)
    expect(stepNeedsTourChatRow({ id: 'chats-messages' })).toBe(true)
    expect(stepNeedsTourChatRow({ id: 'chats-emoji-easter' })).toBe(true)
    expect(stepNeedsTourChatRow({ selector: tourAnchorSelector('chats-new') })).toBe(false)
  })

  it('stepNeedsTourChatSeed covers sidebar and new-chat before the menu step', () => {
    expect(stepNeedsTourChatSeed({ id: 'chats-sidebar' })).toBe(true)
    expect(stepNeedsTourChatSeed({ id: 'chats-new' })).toBe(true)
    expect(stepNeedsTourChatSeed({ id: 'chats-row' })).toBe(true)
    expect(stepNeedsTourChatSeed({ id: 'search' })).toBe(false)
  })

  it('stepNeedsTourChatHref is only for thread steps', () => {
    expect(stepNeedsTourChatHref({ id: 'chats-row' })).toBe(false)
    expect(stepNeedsTourChatHref({ id: 'chats-sidebar' })).toBe(false)
    expect(stepNeedsTourChatHref({ id: 'chats-thread-header' })).toBe(true)
    expect(stepNeedsTourChatHref({ id: 'chats-messages' })).toBe(true)
  })
})
