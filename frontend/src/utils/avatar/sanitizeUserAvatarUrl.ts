/**
 * Отсекает legacy MinIO user-avatar URL и опасные схемы (javascript:/data:/protocol-relative).
 * Остальное (EA photo proxy, group MinIO) пропускает как есть.
 */
export function isLegacyMinioUserAvatarUrl(url: string | null | undefined): boolean {
  if (!url) return false
  const u = url.toLowerCase()
  // Presigned MinIO / S3 для user-аватаров; group chat avatars тоже MinIO, но пути avatars/chats/
  if (u.includes('x-amz-algorithm') || u.includes('x-amz-signature') || u.includes('x-amz-credential')) {
    // user keys были avatars/<hash>/…; group — avatars/chats/
    if (u.includes('/avatars/chats/')) return false
    if (u.includes('/avatars/') || u.includes('%2favatars%2f')) return true
  }
  if (u.includes('/avatars/') && !u.includes('/portal/users/') && !u.includes('/avatars/chats/')) {
    return true
  }
  return false
}

function isDangerousAvatarUrl(url: string): boolean {
  const trimmed = url.trim()
  const lower = trimmed.toLowerCase()
  if (trimmed.startsWith('//')) return true
  if (lower.startsWith('javascript:') || lower.startsWith('data:') || lower.startsWith('vbscript:')) {
    return true
  }
  return false
}

function isBarePortalUserResourceUrl(url: string): boolean {
  const path = url.split('?')[0]?.split('#')[0] ?? ''
  return /\/api\/v1\/portal\/users\/[^/]+\/?$/.test(path)
}

export function sanitizeUserAvatarUrl(url: string | null | undefined): string | null | undefined {
  if (url == null || url === '') return url
  if (isDangerousAvatarUrl(url)) return null
  if (isLegacyMinioUserAvatarUrl(url)) return null
  if (isBarePortalUserResourceUrl(url)) return null
  return url
}
