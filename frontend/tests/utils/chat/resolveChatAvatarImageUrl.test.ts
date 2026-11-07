import { describe, expect, it } from 'vitest'

import { resolveChatAvatarImageUrl } from '@/utils/chat/resolveChatAvatarImageUrl'

const proxy = '/api/v1/portal/users/peer-1/photo?exp=1&sig=x'
const groupMinio =
  'https://localhost:9063/chat-attachments/avatars/chats/g/face.jpg?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Signature=abc'
const legacyUserMinio =
  'https://localhost:9063/chat-attachments/avatars/ab/cd.jpg?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Signature=abc'

describe('resolveChatAvatarImageUrl', () => {
  it('для DM берёт фото пира из каталога', () => {
    expect(
      resolveChatAvatarImageUrl({
        isDirect: true,
        peerSub: 'peer-1',
        userAvatarBySub: { 'peer-1': proxy },
        chatAvatarUrl: null,
      }),
    ).toBe(proxy)
  })

  it('для DM без пира в каталоге падает на chat.avatar_url', () => {
    expect(
      resolveChatAvatarImageUrl({
        isDirect: true,
        peerSub: 'peer-1',
        userAvatarBySub: {},
        chatAvatarUrl: proxy,
      }),
    ).toBe(proxy)
  })

  it('для DM без peer и без URL — пусто', () => {
    expect(
      resolveChatAvatarImageUrl({
        isDirect: true,
        peerSub: null,
        userAvatarBySub: { other: proxy },
        chatAvatarUrl: null,
      }),
    ).toBeNull()
  })

  it('для группы берёт chat.avatar_url и игнорирует каталог', () => {
    expect(
      resolveChatAvatarImageUrl({
        isDirect: false,
        peerSub: 'peer-1',
        userAvatarBySub: { 'peer-1': proxy },
        chatAvatarUrl: groupMinio,
      }),
    ).toBe(groupMinio)
  })

  it('отбрасывает legacy MinIO user-avatar', () => {
    expect(
      resolveChatAvatarImageUrl({
        isDirect: true,
        peerSub: 'peer-1',
        userAvatarBySub: { 'peer-1': legacyUserMinio },
        chatAvatarUrl: legacyUserMinio,
      }),
    ).toBeNull()
  })

  it('отбрасывает javascript: и protocol-relative', () => {
    expect(
      resolveChatAvatarImageUrl({
        isDirect: true,
        peerSub: 'peer-1',
        userAvatarBySub: { 'peer-1': 'javascript:alert(1)' },
        chatAvatarUrl: '//evil.example/a.png',
      }),
    ).toBeNull()
  })
})
