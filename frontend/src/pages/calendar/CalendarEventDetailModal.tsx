import { Modal } from '../../components/ui/Modal'
import { reminderOffsetLabelRu } from '../../domain/calendar/calendarReminderPresets'
import { formatDayLabel, formatTime } from '../../domain/calendar/calendarRrule'
import { usePortalUserDirectory } from '../../hooks/usePortalUserDirectory'
import { TOUR_DEMO_EVENT_TITLE } from '../../onboarding/ensureTourDemoEvent'
import type { PortalCalendarOccurrence } from '../../types/calendar'
import { splitTextWithLinks } from '../../utils/html/splitTextWithLinks'
import styles from '@/styles/modules/calendar/CalendarPage.module.css'

type Props = {
  occurrence: PortalCalendarOccurrence
  deletePending: boolean
  canEdit: boolean
  actionError?: string | null
  onClose: () => void
  onDelete: () => void
  onEdit: () => void
}

function LinkedText({ text }: { text: string }) {
  const parts = splitTextWithLinks(text)
  return (
    <>
      {parts.map((p, i) =>
        p.type === 'link' ? (
          <a
            key={`${p.value}-${i}`}
            href={p.value}
            target="_blank"
            rel="noopener noreferrer"
          >
            {p.value}
          </a>
        ) : (
          <span key={`${p.value}-${i}`}>{p.value}</span>
        ),
      )}
    </>
  )
}

function organizerLabel(
  occurrence: PortalCalendarOccurrence,
  getLabel: (sub: string | null | undefined, fallback?: string) => string,
): string {
  const fromDirectory = getLabel(occurrence.organizer_sub, '')
  if (fromDirectory && fromDirectory !== occurrence.organizer_sub) {
    return fromDirectory
  }
  const attendeeEmail = occurrence.attendees.find(
    (a) => a.user_sub === occurrence.organizer_sub,
  )?.email
  return attendeeEmail || fromDirectory || occurrence.organizer_sub
}

export function CalendarEventDetailModal({
  occurrence,
  deletePending,
  canEdit,
  actionError = null,
  onClose,
  onDelete,
  onEdit,
}: Props) {
  const { getLabel } = usePortalUserDirectory()
  const timeRange = occurrence.ends_at
    ? `${formatTime(occurrence.starts_at)}–${formatTime(occurrence.ends_at)}`
    : formatTime(occurrence.starts_at)

  return (
    <Modal title={occurrence.title} onClose={onClose} maxWidth={480}>
      <div
        className={styles.modalForm}
        {...(occurrence.title === TOUR_DEMO_EVENT_TITLE
          ? { 'data-tour': 'calendar-event-detail' }
          : {})}
      >
        {actionError ? (
          <p className="form-error" role="alert">
            {actionError}
          </p>
        ) : null}
        {occurrence.is_peer_view && !canEdit ? (
          <p className={styles.fieldLabel}>Календарь участника (только просмотр)</p>
        ) : null}
        <p className={styles.fieldLabel}>
          Организатор: {organizerLabel(occurrence, getLabel)}
        </p>
        <p>
          {formatDayLabel(new Date(occurrence.starts_at))} · {timeRange}
        </p>
        {occurrence.location ? (
          <p>
            Место: <LinkedText text={occurrence.location} />
          </p>
        ) : null}
        {occurrence.description ? (
          <p>
            <LinkedText text={occurrence.description} />
          </p>
        ) : null}
        {occurrence.attendees.length ? (
          <p>
            Участники: {occurrence.attendees.map((a) => a.email).join(', ')}
          </p>
        ) : null}
        {occurrence.reminders.length ? (
          <p>
            Напоминания:{' '}
            {occurrence.reminders.map((r) => reminderOffsetLabelRu(r.offset_minutes)).join(', ')}
          </p>
        ) : null}
        <div className={styles.actions}>
          <button type="button" className="btn-secondary" onClick={onClose}>
            Закрыть
          </button>
          {canEdit ? (
            <button type="button" className="btn-secondary" onClick={onEdit}>
              Изменить
            </button>
          ) : null}
          {canEdit ? (
            <button
              type="button"
              className={`btn-secondary ${styles.deleteBtn}`}
              onClick={onDelete}
              disabled={deletePending}
            >
              Удалить
            </button>
          ) : null}
        </div>
      </div>
    </Modal>
  )
}
