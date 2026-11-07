import { useCallback, useEffect, useRef, useState } from 'react'
import { useLocation, useNavigate } from 'react-router'

import {
  getChatInboxBrowserOsEnabled,
  getChatInboxToastEnabled,
} from '@/utils/chat/chatBrowserNotificationSettings'
import {
  shouldShowChatInboxToast,
  shouldSuppressChatInboxToast,
  shouldSuppressDueToMute,
} from '@/utils/chat/chatInboxNotificationRules'
import {
  chatInboxOsNotificationTag,
  closeTrackedChatInboxOsNotification,
  shouldDismissChatInboxToast,
  trackChatInboxOsNotification,
} from '@/utils/notifications/inboxWithdraw'
import { getDmChatNotificationSoundEnabled } from '@/utils/chat/dmChatNotificationSoundSettings'
import { readPortalFocusedChatIds } from '@/utils/chat/portalActiveChatStorage'
import styles from '@/styles/modules/chat/ChatInboxToastLayer.module.css'

type DmDetail = {
  chat_id: string
  kind: 'dm' | 'group'
  author_sub?: string
  preview_text?: string
  is_direct?: boolean
  chat_title?: string | null
  recipient_mentioned?: boolean
}

function inboxToastTitle(d: DmDetail): string {
  const t = d.chat_title?.trim()
  if (t) return t
  return d.kind === 'group' ? 'Групповой чат' : 'Личные сообщения'
}

function inboxToastBody(d: DmDetail): string {
  const p = d.preview_text?.trim()
  if (p) return p
  return 'Новое сообщение'
}

const TOAST_EXIT_MS = 200

export function ChatInboxToastLayer() {
  const navigate = useNavigate()
  const location = useLocation()
  const [toast, setToast] = useState<DmDetail | null>(null)
  const [leaving, setLeaving] = useState(false)
  /** В браузере id таймера — number; в типах с @types/node бывает NodeJS.Timeout. */
  const dismissTimerRef = useRef<number | null>(null)
  const exitTimerRef = useRef<number | null>(null)
  const toastRef = useRef<DmDetail | null>(null)

  useEffect(() => {
    toastRef.current = toast
  }, [toast])

  const clearDismissTimer = useCallback(() => {
    if (dismissTimerRef.current) {
      clearTimeout(dismissTimerRef.current)
      dismissTimerRef.current = null
    }
  }, [])

  const dismiss = useCallback(() => {
    clearDismissTimer()
    if (exitTimerRef.current) clearTimeout(exitTimerRef.current)
    setLeaving(true)
    exitTimerRef.current = window.setTimeout(() => {
      setToast(null)
      setLeaving(false)
    }, TOAST_EXIT_MS)
  }, [clearDismissTimer])

  useEffect(() => {
    function onDm(e: Event) {
      const d = (e as CustomEvent<DmDetail>).detail
      if (!d?.chat_id) return
      const focused = readPortalFocusedChatIds()
      const suppressArgs = {
        eventChatId: d.chat_id,
        pathname: location.pathname,
        search: location.search,
        visibilityState: document.visibilityState,
        focused,
      }
      if (shouldSuppressChatInboxToast(suppressArgs)) {
        return
      }

      const isMentioned = d.recipient_mentioned === true
      const chatMuted = !getDmChatNotificationSoundEnabled(d.chat_id)
      const suppressDueToMute = shouldSuppressDueToMute(chatMuted, isMentioned)

      if (
        shouldShowChatInboxToast({
          ...suppressArgs,
          toastEnabled: getChatInboxToastEnabled(),
          chatMuted,
          isMentioned,
        })
      ) {
        clearDismissTimer()
        setLeaving(false)
        setToast(d)
        dismissTimerRef.current = window.setTimeout(() => {
          dismissTimerRef.current = null
          dismiss()
        }, 6500) as number
      }

      const windowInBackground =
        document.hidden ||
        (typeof document.hasFocus === 'function' && !document.hasFocus())

      // OS-уведомление: показываем если window в фоне.
      // При @упоминании не требуем явного opt-in browser_os — достаточно разрешения браузера.
      const showOsNotif =
        typeof Notification !== 'undefined' &&
        Notification.permission === 'granted' &&
        windowInBackground &&
        !suppressDueToMute &&
        (isMentioned || getChatInboxBrowserOsEnabled())

      if (showOsNotif) {
        try {
          const title = inboxToastTitle(d)
          const body = inboxToastBody(d)
          const url = `${window.location.origin}/chats?chat=${encodeURIComponent(d.chat_id)}`
          const n = new Notification(title, {
            body,
            tag: chatInboxOsNotificationTag(d.chat_id),
            data: { url },
          })
          trackChatInboxOsNotification(d.chat_id, n)
          /** Без onclick страничное уведомление не открывает SPA — SW получает только push из SW. */
          n.onclick = () => {
            n.close()
            window.focus()
            navigate(`/chats?chat=${encodeURIComponent(d.chat_id)}`)
          }
        } catch {
          /* автозапуск / ограничения браузера */
        }
      }
    }
    function onWithdraw(e: Event) {
      const chatId = (e as CustomEvent<{ chat_id?: string }>).detail?.chat_id
      if (!chatId) return
      closeTrackedChatInboxOsNotification(chatId)
      if (shouldDismissChatInboxToast(toastRef.current?.chat_id, chatId)) {
        dismiss()
      }
    }
    window.addEventListener('portal:dm_inbox_update', onDm)
    window.addEventListener('portal:dm_inbox_withdrawn', onWithdraw)
    return () => {
      window.removeEventListener('portal:dm_inbox_update', onDm)
      window.removeEventListener('portal:dm_inbox_withdrawn', onWithdraw)
      clearDismissTimer()
      if (exitTimerRef.current) clearTimeout(exitTimerRef.current)
    }
  }, [location.pathname, location.search, clearDismissTimer, navigate, dismiss])

  if (!toast) return null

  return (
    <div className={styles.wrap} role="status" aria-live="polite">
      <div
        className={`${styles.toast}${leaving ? ` ${styles.toastLeaving}` : ''}`}
        onClick={() => {
          dismiss()
          navigate(`/chats?chat=${encodeURIComponent(toast.chat_id)}`)
        }}
        onKeyDown={(ev) => {
          if (ev.key === 'Enter' || ev.key === ' ') {
            ev.preventDefault()
            dismiss()
            navigate(`/chats?chat=${encodeURIComponent(toast.chat_id)}`)
          }
        }}
        role="button"
        tabIndex={0}
      >
        <div className={styles.toastBody}>
          <p className={styles.toastTitle}>{inboxToastTitle(toast)}</p>
          <p className={styles.toastPreview}>{inboxToastBody(toast)}</p>
        </div>
        <button
          type="button"
          className={styles.closeBtn}
          aria-label="Закрыть"
          onClick={(ev) => {
            ev.stopPropagation()
            dismiss()
          }}
        >
          ×
        </button>
      </div>
    </div>
  )
}
