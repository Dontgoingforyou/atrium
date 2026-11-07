import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import {
  deleteTelegramBind,
  getTelegramBindStatus,
  postTelegramBindInit,
} from '../api/telegram/telegramApi'
import { TELEGRAM_BIND_STATUS_QUERY_KEY } from '../api/queryKeys'
import { AccountAvatarSection } from '../components/account/AccountAvatarSection'
import { AccountChatInboxNotificationsSection } from '../components/account/AccountChatInboxNotificationsSection'
import { AccountDocumentTrashNotificationsSection } from '../components/account/AccountDocumentTrashNotificationsSection'
import { AccountGuidedTourSection } from '../components/account/AccountGuidedTourSection'
import { AccountSoundSettingsSection } from '../components/account/AccountSoundSettingsSection'
import { useAuthStore } from '../store/authStore'
import { useNotifyToast } from '../hooks/useNotifyToast'
import { userFacingMessageFromUnknown } from '../utils/apiUserMessage'
import { openExternalUrl } from '../utils/safeExternalUrl'
import styles from '@/styles/modules/account/AccountSettingsPage.module.css'

const AWAIT_TELEGRAM_BIND_MS = 120_000
const POLL_BIND_STATUS_MS = 2000

export function AccountSettingsPage() {
  const qc = useQueryClient()
  const isPortalAdmin = useAuthStore((s) => s.user?.is_portal_admin ?? false)
  const [awaitingTelegramBind, setAwaitingTelegramBind] = useState(false)
  const notify = useNotifyToast()

  const statusQ = useQuery({
    queryKey: TELEGRAM_BIND_STATUS_QUERY_KEY,
    queryFn: getTelegramBindStatus,
    refetchInterval: awaitingTelegramBind ? POLL_BIND_STATUS_MS : false,
  })

  useEffect(() => {
    if (!awaitingTelegramBind) return
    const t = window.setTimeout(() => setAwaitingTelegramBind(false), AWAIT_TELEGRAM_BIND_MS)
    return () => window.clearTimeout(t)
  }, [awaitingTelegramBind])

  useEffect(() => {
    if (!awaitingTelegramBind || !statusQ.data?.bound) return
    const t = window.setTimeout(() => {
      setAwaitingTelegramBind(false)
      void qc.invalidateQueries({ queryKey: TELEGRAM_BIND_STATUS_QUERY_KEY })
    }, 0)
    return () => window.clearTimeout(t)
  }, [awaitingTelegramBind, statusQ.data?.bound, qc])

  const initMut = useMutation({
    mutationFn: postTelegramBindInit,
    onSuccess: (data) => {
      setAwaitingTelegramBind(true)
      if (!openExternalUrl(data.bot_url, { restrictToAllowlist: true })) {
        notify('Не удалось открыть ссылку на Telegram-бота')
      }
      void qc.invalidateQueries({ queryKey: TELEGRAM_BIND_STATUS_QUERY_KEY })
    },
    onError: (e) => notify(userFacingMessageFromUnknown(e)),
  })

  const unlinkMut = useMutation({
    mutationFn: deleteTelegramBind,
    onSuccess: () => void qc.invalidateQueries({ queryKey: TELEGRAM_BIND_STATUS_QUERY_KEY }),
    onError: (e) => notify(userFacingMessageFromUnknown(e)),
  })

  return (
    <main className={styles.pageRoot}>
      <h1 className={styles.pageTitle}>Аккаунт</h1>

      <AccountAvatarSection />

      <section className={styles.section} aria-labelledby="account-telegram-heading">
        <h2 id="account-telegram-heading" className="section-heading">
          Telegram
        </h2>
        <div className={styles.stack}>
          <p className={styles.lead}>
            Дублируйте уведомления портала в личный чат с ботом. После нажатия «Подключить» откроется Telegram —
            нажмите Start в боте.
          </p>
          {statusQ.isPending && !statusQ.data ? (
            <p className={styles.lead}>Загрузка…</p>
          ) : statusQ.isError ? (
            <p className={styles.lead}>Не удалось загрузить статус.</p>
          ) : statusQ.data?.bound ? (
            <>
              <p className={styles.bodyText}>Подключено{boundSinceSuffix(statusQ.data.created_at)}</p>
              <button
                type="button"
                className={`btn-secondary ${styles.actionBtn}`}
                disabled={unlinkMut.isPending}
                onClick={() => unlinkMut.mutate()}
              >
                {unlinkMut.isPending ? 'Отвязка…' : 'Отключить Telegram'}
              </button>
            </>
          ) : (
            <>
              {awaitingTelegramBind ? (
                <p className={styles.lead}>Ожидаем подтверждение в Telegram… статус обновится сам.</p>
              ) : null}
              <button
                type="button"
                className={`btn-primary ${styles.actionBtn}`}
                disabled={initMut.isPending}
                onClick={() => initMut.mutate()}
              >
                {initMut.isPending ? 'Запрос…' : 'Подключить Telegram'}
              </button>
            </>
          )}
        </div>
      </section>

      <AccountChatInboxNotificationsSection />
      {isPortalAdmin ? <AccountDocumentTrashNotificationsSection /> : null}
      <AccountSoundSettingsSection />
      <AccountGuidedTourSection />
    </main>
  )
}

function boundSinceSuffix(createdAt: string | null): string {
  if (!createdAt) return '.'
  const d = new Date(createdAt)
  if (Number.isNaN(d.getTime())) return '.'
  return ` с ${d.toLocaleString('ru-RU')}.`
}
