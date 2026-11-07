import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'

import { setCalendarShow } from '../../api/calendar/calendarApi'
import { IconTrash } from '../../components/icons/portalIcons'
import { ConfirmDialog } from '../../components/ui/ConfirmDialog'
import { toColorInputValue } from '../../domain/calendar/calendarColor'
import { useNotifyToast } from '../../hooks/useNotifyToast'
import { useAuthStore } from '../../store/authStore'
import type { PortalCalendar } from '../../types/calendar'
import { userFacingMessageFromUnknown } from '../../utils/apiUserMessage'
import { calendarQueryKeys } from './calendarQueryKeys'
import { defaultOwnCalendarId, ownCalendars } from './calendarOwn'
import styles from '@/styles/modules/calendar/CalendarPage.module.css'

type Props = {
  calendars: PortalCalendar[]
  activeIds: string[]
  peerViewActive?: boolean
  onToggle: (id: string) => void
  onUpdate: (id: string, patch: { title?: string; color?: string }) => void
  onCreate: () => void
  onDelete: (id: string) => void
  updatePending: boolean
  createPending: boolean
  deletePending: boolean
}

export function CalendarSidebar({
  calendars,
  activeIds,
  peerViewActive = false,
  onToggle,
  onUpdate,
  onCreate,
  onDelete,
  updatePending,
  createPending,
  deletePending,
}: Props) {
  const isAdmin = useAuthStore((s) => s.user?.is_portal_admin ?? false)
  const notify = useNotifyToast()
  const qc = useQueryClient()
  const [editingId, setEditingId] = useState<string | null>(null)
  const [draftTitle, setDraftTitle] = useState('')
  const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null)
  const owned = ownCalendars(calendars)
  const ownCalendar = owned.find((calendar) => calendar.id === defaultOwnCalendarId(calendars)) ?? null
  const showMut = useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) => setCalendarShow(id, enabled),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: calendarQueryKeys.calendars })
      await qc.invalidateQueries({ queryKey: calendarQueryKeys.shared })
    },
    onError: (error) => notify(userFacingMessageFromUnknown(error), { tone: 'error' }),
  })
  const pendingDelete = pendingDeleteId
    ? (owned.find((calendar) => calendar.id === pendingDeleteId) ?? null)
    : null

  function startEdit(calendar: PortalCalendar) {
    setEditingId(calendar.id)
    setDraftTitle(calendar.title)
  }

  function commitTitle(calendar: PortalCalendar) {
    const next = draftTitle.trim()
    setEditingId(null)
    if (!next || next === calendar.title) return
    onUpdate(calendar.id, { title: next })
  }

  return (
    <aside
      className={`${styles.sidebar}${peerViewActive ? ` ${styles.sidebarPeerMuted}` : ''}`}
      data-tour="calendar-sidebar"
    >
      <h2 className={styles.sidebarTitle}>Календари</h2>
      {peerViewActive ? (
        <p className={styles.peerViewHint} role="status">
          Показан календарь участника. Свои календари временно скрыты с сетки.
        </p>
      ) : null}
      <ul className={styles.calList}>
        {owned.map((calendar) => {
          const canDelete = !calendar.is_primary
          const editing = editingId === calendar.id
          return (
            <li key={calendar.id} className={styles.calItem}>
              <input
                type="checkbox"
                checked={activeIds.includes(calendar.id)}
                onChange={() => onToggle(calendar.id)}
                disabled={peerViewActive}
                aria-label={calendar.title}
              />
              <label
                className={styles.calColorSwatch}
                style={{ background: calendar.color }}
                title={`Изменить цвет ${calendar.color}`}
              >
                <input
                  type="color"
                  className={styles.calColorInput}
                  value={toColorInputValue(calendar.color)}
                  disabled={updatePending}
                  onChange={(event) => onUpdate(calendar.id, { color: event.target.value })}
                  aria-label={`Цвет календаря ${calendar.title}`}
                />
              </label>
              {editing ? (
                <input
                  className={`form-input ${styles.calTitleInput}`}
                  value={draftTitle}
                  autoFocus
                  onChange={(event) => setDraftTitle(event.target.value)}
                  onBlur={() => commitTitle(calendar)}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter') commitTitle(calendar)
                    if (event.key === 'Escape') setEditingId(null)
                  }}
                  aria-label="Название календаря"
                />
              ) : (
                <button
                  type="button"
                  className={styles.calLabelBtn}
                  onClick={() => startEdit(calendar)}
                  title="Переименовать"
                >
                  <span className={styles.calLabel}>{calendar.title}</span>
                </button>
              )}
              {canDelete ? (
                <button
                  type="button"
                  className={styles.calDeleteBtn}
                  title="Удалить календарь"
                  aria-label={`Удалить календарь «${calendar.title}»`}
                  disabled={deletePending}
                  onClick={() => setPendingDeleteId(calendar.id)}
                >
                  <IconTrash />
                </button>
              ) : null}
            </li>
          )
        })}
      </ul>
      {isAdmin && ownCalendar ? (
        <label className={styles.calShow}>
          <input
            type="checkbox"
            checked={ownCalendar.show_to_other_departments}
            disabled={showMut.isPending}
            onChange={(event) =>
              showMut.mutate({ id: ownCalendar.id, enabled: event.target.checked })
            }
          />
          Показывать другим отделам
        </label>
      ) : null}
      <div className={styles.sidebarActions}>
        <button
          type="button"
          className="btn-secondary"
          data-tour="calendar-create-calendar"
          onClick={onCreate}
          disabled={createPending}
        >
          {createPending ? 'Создание…' : 'Новый календарь'}
        </button>
      </div>

      {pendingDelete ? (
        <ConfirmDialog
          open
          title="Удалить календарь?"
          message={`Календарь «${pendingDelete.title}» и все его события будут удалены без возможности восстановления.`}
          confirmLabel="Удалить"
          cancelLabel="Отмена"
          destructive
          confirmSound="error"
          disabled={deletePending}
          onConfirm={() => onDelete(pendingDelete.id)}
          onCancel={() => {
            if (!deletePending) setPendingDeleteId(null)
          }}
        />
      ) : null}
    </aside>
  )
}
