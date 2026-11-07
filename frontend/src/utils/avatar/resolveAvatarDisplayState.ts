export type AvatarDisplayState =
  | { kind: 'none' }
  | { kind: 'pending' }
  | { kind: 'url'; href: string }

type Args = {
  cleanUrl: string | null | undefined
  isPhotoProxy: boolean
  canFetchProxy: boolean
  blobUrl: string | null
  proxyFailed: boolean
}

export function resolveAvatarDisplayState({
  cleanUrl,
  isPhotoProxy,
  canFetchProxy,
  blobUrl,
  proxyFailed,
}: Args): AvatarDisplayState {
  if (cleanUrl == null || cleanUrl === '') {
    return { kind: 'none' }
  }
  if (!isPhotoProxy) {
    return { kind: 'url', href: cleanUrl }
  }
  if (!canFetchProxy || proxyFailed) {
    return { kind: 'none' }
  }
  if (blobUrl) {
    return { kind: 'url', href: blobUrl }
  }
  return { kind: 'pending' }
}

export function avatarInnerKind(
  displayedUrl: string | null | undefined,
  failedUrl: string | null,
): 'img' | 'initials' {
  const showImg = Boolean(displayedUrl) && failedUrl !== displayedUrl
  return showImg ? 'img' : 'initials'
}
