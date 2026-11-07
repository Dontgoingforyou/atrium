import { describe, expect, it } from 'vitest'

import { isLegacyMinioUserAvatarUrl, sanitizeUserAvatarUrl } from '@/utils/avatar/sanitizeUserAvatarUrl'

describe('sanitizeUserAvatarUrl', () => {
  it('отбрасывает presigned MinIO user-avatar', () => {
    const url =
      'https://localhost:9063/chat-attachments/avatars/ab/cd.jpg?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Signature=abc'
    expect(isLegacyMinioUserAvatarUrl(url)).toBe(true)
    expect(sanitizeUserAvatarUrl(url)).toBeNull()
  })

  it('оставляет EA proxy и group chat MinIO', () => {
    expect(sanitizeUserAvatarUrl('/api/v1/portal/users/u1/photo?exp=1&sig=x')).toBe(
      '/api/v1/portal/users/u1/photo?exp=1&sig=x',
    )
    const group =
      'https://localhost:9063/chat-attachments/avatars/chats/g/face.jpg?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Signature=abc'
    expect(isLegacyMinioUserAvatarUrl(group)).toBe(false)
    expect(sanitizeUserAvatarUrl(group)).toBe(group)
  })

  it('отбрасывает GET /portal/users/{id} без /photo — это не картинка', () => {
    expect(sanitizeUserAvatarUrl('/api/v1/portal/users/8fc273a0-82a8-4e6a-b286-9050d24a0d9f')).toBeNull()
    expect(
      sanitizeUserAvatarUrl(
        'https://cosmolet.stage.example.com/api/v1/portal/users/3c7bb67c-2c1e-4533-8991-884043b35f60',
      ),
    ).toBeNull()
    expect(sanitizeUserAvatarUrl('/api/v1/portal/users/u1/')).toBeNull()
  })

  it('отбрасывает javascript:/data:/protocol-relative', () => {
    expect(sanitizeUserAvatarUrl('javascript:alert(1)')).toBeNull()
    expect(sanitizeUserAvatarUrl('data:image/png;base64,xx')).toBeNull()
    expect(sanitizeUserAvatarUrl('//evil.example/a.png')).toBeNull()
    expect(sanitizeUserAvatarUrl(null)).toBeNull()
  })
})
