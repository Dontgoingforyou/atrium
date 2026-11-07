import { describe, expect, it } from 'vitest'

import { portalUsersAvatarBySub } from '@/utils/avatar/portalUsersAvatarBySub'

const proxy = '/api/v1/portal/users/u1/photo?exp=1&sig=x'
const legacy =
  'https://localhost:9063/chat-attachments/avatars/ab/cd.jpg?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Signature=abc'

describe('portalUsersAvatarBySub', () => {
  it('оставляет EA proxy и отсекает legacy MinIO', () => {
    const map = portalUsersAvatarBySub([
      { sub: 'u1', avatar_url: proxy },
      { sub: 'u2', avatar_url: legacy },
      { sub: 'u3', avatar_url: null },
    ])
    expect(map.u1).toBe(proxy)
    expect(map.u2).toBeUndefined()
    expect(map.u3).toBeUndefined()
  })
})
