import { useEffect, useState } from 'react'

import { useAuthStore } from '../store/authStore'
import {
  resolveAvatarDisplayState,
  type AvatarDisplayState,
} from '../utils/avatar/resolveAvatarDisplayState'
import { sanitizeUserAvatarUrl } from '../utils/avatar/sanitizeUserAvatarUrl'

function isPortalUserPhotoProxyUrl(url: string): boolean {
  return /\/api\/v1\/portal\/users\/[^/]+\/photo\?/.test(url)
}

/** Для proxy-URL фото EA подгружаем blob с Bearer; иначе отдаём URL как есть. */
export function useResolvedAvatarUrl(imageUrl: string | null | undefined): AvatarDisplayState {
  const accessToken = useAuthStore((s) => s.accessToken)
  const clean = sanitizeUserAvatarUrl(imageUrl)
  const isPhotoProxy = Boolean(clean && isPortalUserPhotoProxyUrl(clean))
  const needsProxy = Boolean(isPhotoProxy && accessToken)
  const fetchKey = needsProxy && clean && accessToken ? `${clean}\0${accessToken}` : null
  const [blobUrl, setBlobUrl] = useState<string | null>(null)
  const [proxyFailed, setProxyFailed] = useState(false)
  const [seenFetchKey, setSeenFetchKey] = useState<string | null>(null)

  if (seenFetchKey !== fetchKey) {
    setSeenFetchKey(fetchKey)
    setBlobUrl(null)
    setProxyFailed(false)
  }

  useEffect(() => {
    if (fetchKey == null || !clean || !accessToken) {
      return
    }
    let objectUrl: string | null = null
    let cancelled = false
    const href = clean.startsWith('http')
      ? clean
      : `${window.location.origin}${clean.startsWith('/') ? clean : `/${clean}`}`

    void fetch(href, {
      headers: { Authorization: `Bearer ${accessToken}` },
      credentials: 'include',
    })
      .then(async (res) => {
        if (!res.ok) throw new Error(String(res.status))
        return res.blob()
      })
      .then((blob) => {
        if (cancelled) return
        objectUrl = URL.createObjectURL(blob)
        setBlobUrl(objectUrl)
      })
      .catch(() => {
        if (!cancelled) {
          setBlobUrl(null)
          setProxyFailed(true)
        }
      })

    return () => {
      cancelled = true
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [fetchKey, clean, accessToken])

  return resolveAvatarDisplayState({
    cleanUrl: clean,
    isPhotoProxy,
    canFetchProxy: needsProxy,
    blobUrl: needsProxy ? blobUrl : null,
    proxyFailed: needsProxy ? proxyFailed : false,
  })
}
