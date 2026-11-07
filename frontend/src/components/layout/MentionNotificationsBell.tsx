import { useEffect, useRef, useState } from 'react'
import { useClickOutside } from '../../hooks/useClickOutside'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router'

import {
  deleteAllNotifications,
  deleteNotification,
  getUnreadCount,
  listNotifications,
  markAllNotificationsRead,
  markNotificationRead,
} from '../../api/notifications/notificationsApi'
import {
  PORTAL_NOTIFICATIONS_LIST_QUERY_KEY,
  PORTAL_NOTIFICATIONS_ROOT_QUERY_KEY,
  PORTAL_NOTIFICATIONS_UNREAD_COUNT_QUERY_KEY,
} from '../../api/queryKeys'
import { useScheduleDeleteWithUndo } from '../../hooks/useScheduleDeleteWithUndo'
import { useNotifyToast } from '../../hooks/useNotifyToast'
import { useAuthStore } from '../../store/authStore'
import type { PortalNotification } from '../../types/notification'
import { IconBell } from '../icons/portalIcons'
import { ConfirmDialog } from '../ui/ConfirmDialog'
import { IconVolumeOff, IconVolumeOn } from '../icons/VolumeNotificationIcons'
import {
  getNotificationSoundEnabled,
  playNotificationSound,
  setNotificationSoundEnabled,
} from '../../utils/notifications/notificationSound'
import { userFacingMessageFromUnknown } from '../../utils/apiUserMessage'
import { NotificationItemRow } from './MentionNotificationsBellItem'
import { UI_SOUND_SKIP_VALUE } from '@/constants/uiSounds'
import styles from '@/styles/modules/layout/MentionNotificationsBell.module.css'

/** Редкий safety-net, если WS инбокса не доставил событие. */
const NOTIF_SAFETY_REFETCH_MS = 8 * 60_000

interface Props {
  open: boolean
  onToggle: () => void
}

export function MentionNotificationsBell({ open, onToggle }: Props) {
  const user = useAuthStore((s) => s.user)
  const navigate = useNavigate()
  const qc = useQueryClient()
  const notify = useNotifyToast()
  const popoverRef = useRef<HTMLDivElement>(null)
  const [soundEnabled, setSoundEnabled] = useState(getNotificationSoundEnabled)

  const { data: countData, isError: countError, error: countErr } = useQuery({
    queryKey: PORTAL_NOTIFICATIONS_UNREAD_COUNT_QUERY_KEY,
    queryFn: getUnreadCount,
    refetchInterval: NOTIF_SAFETY_REFETCH_MS,
    refetchOnWindowFocus: true,
    enabled: Boolean(user),
  })

  const { data: notifications = [], isError: listError, error: listErr } = useQuery({
    queryKey: PORTAL_NOTIFICATIONS_LIST_QUERY_KEY,
    queryFn: () => listNotifications({ unread_only: false, limit: 50 }),
    refetchInterval: NOTIF_SAFETY_REFETCH_MS,
    refetchOnWindowFocus: true,
    enabled: Boolean(user),
  })

  useEffect(() => {
    if (countError) notify(userFacingMessageFromUnknown(countErr))
  }, [countError, countErr, notify])
  useEffect(() => {
    if (listError) notify(userFacingMessageFromUnknown(listErr))
  }, [listError, listErr, notify])

  const markOneMutation = useMutation({
    mutationFn: (id: string) => markNotificationRead(id),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: PORTAL_NOTIFICATIONS_ROOT_QUERY_KEY })
    },
    onError: (e: unknown) => notify(userFacingMessageFromUnknown(e)),
  })

  const markAllMutation = useMutation({
    mutationFn: markAllNotificationsRead,
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: PORTAL_NOTIFICATIONS_ROOT_QUERY_KEY })
    },
    onError: (e: unknown) => notify(userFacingMessageFromUnknown(e)),
  })

  const deleteOneMutation = useMutation({
    mutationFn: (id: string) => deleteNotification(id),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: PORTAL_NOTIFICATIONS_ROOT_QUERY_KEY })
    },
    onError: (e: unknown) => notify(userFacingMessageFromUnknown(e)),
  })

  const deleteAllMutation = useMutation({
    mutationFn: deleteAllNotifications,
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: PORTAL_NOTIFICATIONS_ROOT_QUERY_KEY })
    },
    onError: (e: unknown) => notify(userFacingMessageFromUnknown(e)),
  })

  const scheduleDeleteWithUndo = useScheduleDeleteWithUndo()
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null)
  const [confirmDeleteAllOpen, setConfirmDeleteAllOpen] = useState(false)

  useEffect(() => {
    function handleNotifEvent() {
      void playNotificationSound()
    }
    window.addEventListener('portal:notification_update', handleNotifEvent)
    return () => window.removeEventListener('portal:notification_update', handleNotifEvent)
  }, [])

  useClickOutside(open, [popoverRef], onToggle, 'mousedown')

  const unreadCount = countData?.unread_count ?? 0
  const notifLabel =
    unreadCount > 0
      ? `Уведомления, непрочитано: ${unreadCount > 99 ? '99+' : unreadCount}`
      : 'Уведомления'
  const notifTitle = unreadCount > 0 ? `Уведомления (${unreadCount > 99 ? '99+' : unreadCount})` : 'Уведомления'

  function handleItemClick(notif: PortalNotification) {
    markOneMutation.mutate(notif.id)
    onToggle()
    if (notif.type === 'document_mention' && notif.document_id) {
      navigate(`/documents/${encodeURIComponent(notif.document_id)}`)
      return
    }
    if (notif.type === 'document_trashed') {
      navigate('/p/trash')
      return
    }
    if (notif.type.startsWith('calendar_')) {
      if (notif.calendar_event_id) {
        navigate(`/calendar?event=${encodeURIComponent(notif.calendar_event_id)}`)
      } else if (notif.calendar_id) {
        navigate(`/calendar?calendar=${encodeURIComponent(notif.calendar_id)}`)
      } else {
        navigate('/calendar')
      }
      return
    }
    if (notif.task_id) {
      navigate(`/tasks/${encodeURIComponent(notif.task_id)}`)
    }
  }

  function requestDeleteOne(id: string) {
    setConfirmDeleteId(id)
  }

  function cancelDeleteOne() {
    setConfirmDeleteId(null)
  }

  function confirmDeleteOne() {
    const id = confirmDeleteId
    setConfirmDeleteId(null)
    if (!id) return

    const previous = qc.getQueryData<PortalNotification[]>(PORTAL_NOTIFICATIONS_LIST_QUERY_KEY)
    scheduleDeleteWithUndo({
      message: 'Уведомление удалено',
      optimistic: () => {
        qc.setQueryData<PortalNotification[]>(PORTAL_NOTIFICATIONS_LIST_QUERY_KEY, (old) =>
          old?.filter((n) => n.id !== id),
        )
      },
      revert: () => {
        if (previous !== undefined) {
          qc.setQueryData(PORTAL_NOTIFICATIONS_LIST_QUERY_KEY, previous)
        }
      },
      commit: () => deleteOneMutation.mutate(id),
    })
  }

  function requestDeleteAll() {
    setConfirmDeleteAllOpen(true)
  }

  function cancelDeleteAll() {
    setConfirmDeleteAllOpen(false)
  }

  function confirmDeleteAll() {
    setConfirmDeleteAllOpen(false)
    const previous = qc.getQueryData<PortalNotification[]>(PORTAL_NOTIFICATIONS_LIST_QUERY_KEY)
    scheduleDeleteWithUndo({
      message: 'Все уведомления удалены',
      optimistic: () => {
        qc.setQueryData<PortalNotification[]>(PORTAL_NOTIFICATIONS_LIST_QUERY_KEY, [])
      },
      revert: () => {
        if (previous !== undefined) {
          qc.setQueryData(PORTAL_NOTIFICATIONS_LIST_QUERY_KEY, previous)
        }
      },
      commit: () => deleteAllMutation.mutate(),
    })
  }

  function handleSoundToggle(e: React.MouseEvent) {
    e.stopPropagation()
    const next = !soundEnabled
    setNotificationSoundEnabled(next)
    setSoundEnabled(next)
    if (next) {
      void playNotificationSound()
    }
  }

  return (
    <div className={styles.triggerWrapper} ref={popoverRef} data-tour="notifications">
      <div className={styles.bellWrap}>
        <button
          type="button"
          className={`${styles.bellBtn}${open ? ` ${styles.bellBtnActive}` : ''}`}
          onClick={onToggle}
          title={notifTitle}
          aria-label={notifLabel}
          aria-expanded={open}
        >
          <IconBell />
        </button>
        {unreadCount > 0 ? (
          <span className={styles.unreadBadge} aria-hidden>
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        ) : null}
      </div>

      {open && (
        <div className={styles.popover}>
          <div className={styles.popoverHeader}>
            <span className={styles.popoverTitle}>Уведомления</span>
            <div className={styles.popoverHeaderActions}>
              <button
                type="button"
                className={styles.soundToggleBtn}
                data-ui-sound={UI_SOUND_SKIP_VALUE}
                onClick={handleSoundToggle}
                title={
                  soundEnabled
                    ? 'Выключить звук (упоминания и личные чаты)'
                    : 'Включить звук (упоминания и личные чаты)'
                }
                aria-pressed={soundEnabled}
                aria-label={
                  soundEnabled
                    ? 'Звук уведомлений включён: упоминания и личные чаты'
                    : 'Звук уведомлений выключен: упоминания и личные чаты'
                }
              >
                {soundEnabled ? <IconVolumeOn /> : <IconVolumeOff />}
              </button>
              {unreadCount > 0 && (
                <button
                  type="button"
                  className={styles.clearBtn}
                  onClick={() => markAllMutation.mutate()}
                  disabled={markAllMutation.isPending}
                >
                  Прочитать все
                </button>
              )}
              {notifications.length > 0 && (
                <button
                  type="button"
                  className={styles.clearBtn}
                  onClick={requestDeleteAll}
                  disabled={deleteAllMutation.isPending}
                >
                  Удалить все
                </button>
              )}
            </div>
          </div>

          <div className={styles.list}>
            {notifications.length === 0 ? (
              <p className={styles.empty}>Нет уведомлений</p>
            ) : (
              notifications.map((notif) => (
                <NotificationItemRow
                  key={notif.id}
                  notif={notif}
                  onItemClick={handleItemClick}
                  onDelete={requestDeleteOne}
                  deletePending={
                    deleteOneMutation.isPending && deleteOneMutation.variables === notif.id
                  }
                />
              ))
            )}
          </div>
        </div>
      )}

      <ConfirmDialog
        open={confirmDeleteId !== null}
        title="Удалить уведомление?"
        message="Действие можно отменить в течение 5 секунд после удаления."
        confirmLabel="Удалить"
        destructive
        onConfirm={confirmDeleteOne}
        onCancel={cancelDeleteOne}
      />

      <ConfirmDialog
        open={confirmDeleteAllOpen}
        title="Удалить все уведомления?"
        message="Действие можно отменить в течение 5 секунд после удаления."
        confirmLabel="Удалить все"
        destructive
        onConfirm={confirmDeleteAll}
        onCancel={cancelDeleteAll}
      />
    </div>
  )
}
