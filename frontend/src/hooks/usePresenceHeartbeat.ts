import { useEffect, useRef } from 'react'
import { useQueryClient } from '@tanstack/react-query'

import { listPortalUsersPresence, postPortalPresence, type PortalUserShort } from '../api/usersApi'
import { PORTAL_USERS_QUERY_KEY } from '../api/queryKeys'
import { API_BASE } from '../api/rawClient'
import { useAuthStore } from '../store/authStore'
import { mergePortalUsersPresence } from '../utils/mergePortalUsersPresence'

/** Интервал heartbeat; после успешной отправки подтягиваем только presence без refetch аватаров (presigned URL). */
const INTERVAL_MS = 12_000

/**
 * Периодически шлёт heartbeat присутствия (видимость вкладки + активность пользователя).
 */
export function usePresenceHeartbeat(): void {
  const accessToken = useAuthStore((s) => s.accessToken)
  const qc = useQueryClient()
  const lastActiveBumpRef = useRef(0)

  useEffect(() => {
    if (!accessToken) return

    let timer: ReturnType<typeof setInterval> | null = null

    function bumpActivity(): void {
      lastActiveBumpRef.current = Date.now()
    }

    function send(): void {
      const visible = document.visibilityState === 'visible'
      const active =
        visible && Date.now() - lastActiveBumpRef.current < 3 * 60_000
      void postPortalPresence({ visible, active })
        .then(async () => {
          try {
            const rows = await listPortalUsersPresence()
            qc.setQueryData<PortalUserShort[]>(PORTAL_USERS_QUERY_KEY, (prev) => {
              return mergePortalUsersPresence(prev, rows) ?? prev
            })
          } catch {
            /* сеть — тихо */
          }
        })
        .catch(() => {
          /* сеть / 401 — тихо */
        })
    }

    function stopTimer(): void {
      if (timer) {
        clearInterval(timer)
        timer = null
      }
    }

    function startTimer(): void {
      stopTimer()
      timer = setInterval(send, INTERVAL_MS)
    }

    function onVis(): void {
      if (document.visibilityState === 'visible') {
        bumpActivity()
        send()
        startTimer()
      } else {
        stopTimer()
        send()
      }
    }

    const onUser = () => bumpActivity()

    function onPageHide(): void {
      const token = useAuthStore.getState().accessToken
      if (!token) return
      navigator.sendBeacon(
        `${API_BASE}/portal/users/me/presence-beacon`,
        new Blob(
          [JSON.stringify({ access_token: token, visible: false, active: false })],
          { type: 'application/json' },
        ),
      )
    }

    bumpActivity()
    if (document.visibilityState === 'visible') {
      send()
      startTimer()
    } else {
      send()
    }
    document.addEventListener('visibilitychange', onVis)
    window.addEventListener('pagehide', onPageHide)
    window.addEventListener('pointerdown', onUser, true)
    window.addEventListener('keydown', onUser, true)

    return () => {
      stopTimer()
      document.removeEventListener('visibilitychange', onVis)
      window.removeEventListener('pagehide', onPageHide)
      window.removeEventListener('pointerdown', onUser, true)
      window.removeEventListener('keydown', onUser, true)
    }
  }, [accessToken, qc])
}
