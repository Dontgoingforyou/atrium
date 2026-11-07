import { sanitizeUserAvatarUrl } from '../avatar/sanitizeUserAvatarUrl'

type Args = {
  isDirect: boolean
  peerSub: string | null
  userAvatarBySub: Record<string, string | undefined>
  chatAvatarUrl: string | null | undefined
}

export function resolveChatAvatarImageUrl({
  isDirect,
  peerSub,
  userAvatarBySub,
  chatAvatarUrl,
}: Args): string | null | undefined {
  const fromCatalog = isDirect && peerSub ? userAvatarBySub[peerSub] : undefined
  const raw = isDirect ? (fromCatalog ?? chatAvatarUrl) : chatAvatarUrl
  return sanitizeUserAvatarUrl(raw)
}
