import { useCallback, useState } from 'react'

import { fetchPushVapidPublicKey, postPushSubscribe, postPushUnsubscribe } from '../../api/notifications/pushApi'
import { userFacingMessageFromUnknown } from '../../utils/apiUserMessage'
import {
  getChatInboxBrowserOsEnabled,
  getChatInboxToastEnabled,
  getChatWebPushSubscriptionOptIn,
  setChatInboxBrowserOsEnabled,
  setChatInboxToastEnabled,
  setChatWebPushSubscriptionOptIn,
} from '@/utils/chat/chatBrowserNotificationSettings'
import { ensureServiceWorkerRegistered, subscribeCurrentUserToWebPush } from '../../utils/notifications/pushSubscription'
import { notificationPermissionLabelRu } from '../../utils/notifications/notificationPermissionRu'
import shared from '@/styles/modules/account/AccountSettingsPage.module.css'

export function AccountChatInboxNotificationsSection() {
  const [toastOn, setToastOn] = useState(() => getChatInboxToastEnabled())
  const [browserOsOn, setBrowserOsOn] = useState(() => getChatInboxBrowserOsEnabled())
  const [pushOptIn, setPushOptIn] = useState(() => getChatWebPushSubscriptionOptIn())
  const [perm, setPerm] = useState<NotificationPermission>(() =>
    typeof Notification !== 'undefined' ? Notification.permission : 'denied',
  )
  const [status, setStatus] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const onToastToggle = useCallback(() => {
    const next = !getChatInboxToastEnabled()
    setChatInboxToastEnabled(next)
    setToastOn(next)
  }, [])

  const onBrowserOsToggle = useCallback(() => {
    const next = !getChatInboxBrowserOsEnabled()
    setChatInboxBrowserOsEnabled(next)
    setBrowserOsOn(next)
  }, [])

  const requestBrowserPermission = useCallback(async () => {
    setError(null)
    setStatus(null)
    if (typeof Notification === 'undefined') {
      setError('Браузер не поддерживает Notification API')
      return
    }
    try {
      const r = await Notification.requestPermission()
      setPerm(r)
      if (r !== 'granted') {
        setError('Разрешение не получено — системные уведомления недоступны')
      } else {
        setStatus('Разрешение на уведомления получено')
      }
    } catch (e) {
      setError(userFacingMessageFromUnknown(e))
    }
  }, [])

  const onPushCheckedChange = useCallback(async (checked: boolean) => {
    setError(null)
    setStatus(null)
    if (!checked) {
      setChatWebPushSubscriptionOptIn(false)
      setPushOptIn(false)
      try {
        await ensureServiceWorkerRegistered()
        const reg = await navigator.serviceWorker.ready
        const existing = await reg.pushManager.getSubscription()
        if (existing) {
          await postPushUnsubscribe(existing.endpoint)
          await existing.unsubscribe()
        }
        setStatus('Push-уведомления отключены')
      } catch (e) {
        // Отписка не прошла — подписка могла остаться активной на сервере/в браузере:
        // возвращаем тумблер во включённое состояние, иначе UI врёт, что push выключен.
        setChatWebPushSubscriptionOptIn(true)
        setPushOptIn(true)
        setError(userFacingMessageFromUnknown(e))
      }
      return
    }
    try {
      const pk = await fetchPushVapidPublicKey()
      if (!pk) {
        setPushOptIn(false)
        setError('Web Push не настроен на сервере (нет публичного ключа VAPID)')
        return
      }
      await ensureServiceWorkerRegistered()
      const subJson = await subscribeCurrentUserToWebPush(pk)
      await postPushSubscribe(subJson)
      setChatWebPushSubscriptionOptIn(true)
      setPushOptIn(true)
      setStatus('Подписка Web Push сохранена')
    } catch (e) {
      // Браузер мог создать подписку, которую не удалось зарегистрировать на сервере —
      // убираем orphan, чтобы не висела мёртвой записью в pushManager.
      try {
        const reg = await navigator.serviceWorker.ready
        const orphan = await reg.pushManager.getSubscription()
        if (orphan) await orphan.unsubscribe()
      } catch {
        /* best-effort cleanup */
      }
      setChatWebPushSubscriptionOptIn(false)
      setPushOptIn(false)
      setError(userFacingMessageFromUnknown(e))
    }
  }, [])

  return (
    <section className={shared.section} aria-labelledby="account-chat-inbox-heading">
      <h2 id="account-chat-inbox-heading" className="section-heading">
        Уведомления о чатах
      </h2>
      <p className={shared.lead}>
        Всплывающий тост в портале, по желанию — системное уведомление, когда вы не в этом окне, и Web Push, если
        настроен сервер.
      </p>

      <div className={shared.row}>
        <label className={shared.checkboxLabel}>
          <input type="checkbox" checked={toastOn} onChange={onToastToggle} />
          <span>Тост при новом сообщении в чате</span>
        </label>
        <label className={shared.checkboxLabel}>
          <input type="checkbox" checked={browserOsOn} onChange={onBrowserOsToggle} />
          <span>Системное уведомление браузера, когда вкладка в фоне или окно без фокуса</span>
        </label>
      </div>

      <div className={shared.row}>
        <button
          type="button"
          className={`btn-secondary ${shared.actionBtn}`}
          onClick={() => void requestBrowserPermission()}
        >
          Запросить разрешение на уведомления
        </button>
        <span className={shared.metaText}>
          Статус разрешения: {notificationPermissionLabelRu(perm)}
        </span>
      </div>

      <div className={shared.row}>
        <label className={shared.checkboxLabel}>
          <input
            type="checkbox"
            checked={pushOptIn}
            onChange={(e) => void onPushCheckedChange(e.target.checked)}
          />
          <span>Web Push при закрытой вкладке</span>
        </label>
      </div>

      {status ? <p className={shared.metaText}>{status}</p> : null}
      {error ? <p className={shared.feedbackError}>{error}</p> : null}
    </section>
  )
}
