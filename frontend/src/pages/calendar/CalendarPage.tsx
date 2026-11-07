import {
  DndContext,
  DragOverlay,
  PointerSensor,
  pointerWithin,
  useSensor,
  useSensors,
  type DragEndEvent,
  type DragStartEvent,
} from '@dnd-kit/core'
import { useId, useRef, useState } from 'react'
import { UserPicker } from '../../components/common/UserPicker'
import { formatTime } from '../../domain/calendar/calendarRrule'
import { parseCalendarDayDropId } from '../../domain/calendar/occurrenceDayMove'
import { useAuthStore } from '../../store/authStore'
import type { PortalCalendarOccurrence } from '../../types/calendar'
import { contrastingTextOn } from '../../utils/color/contrastingTextOn'
import { CalendarAdminTools } from './CalendarAdminTools'
import { CalendarDayCell } from './CalendarDayCell'
import { CalendarEventDetailModal } from './CalendarEventDetailModal'
import { CalendarEventFormModal } from './CalendarEventFormModal'
import { CalendarEventSearchField } from './CalendarEventSearchField'
import { CalendarSidebar } from './CalendarSidebar'
import { useCalendarEventMove } from './useCalendarEventMove'
import { useCalendarPageController } from './useCalendarPageController'
import { useGuidedTourActive } from '../../hooks/useGuidedTourActive'
import { useNarrowViewport } from '../../hooks/useNarrowViewport'
import styles from '@/styles/modules/calendar/CalendarPage.module.css'
import narrow from '@/styles/modules/calendar/CalendarPageNarrow.module.css'

const WEEKDAYS = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']

function draggedOccurrence(data: { current?: Record<string, unknown> } | undefined): PortalCalendarOccurrence | null {
  const occ = data?.current?.occurrence
  if (!occ || typeof occ !== 'object') return null
  const row = occ as PortalCalendarOccurrence
  if (typeof row.event_id !== 'string' || typeof row.starts_at !== 'string') return null
  return row
}

function DraggedEventChip({ occurrence }: { occurrence: PortalCalendarOccurrence }) {
  const background = occurrence.color || occurrence.calendar_color
  return (
    <div
      className={`${styles.eventChip} ${styles.eventChipOverlay}`}
      style={{ background, color: contrastingTextOn(background) }}
    >
      <span className={styles.eventChipLabel}>
        {formatTime(occurrence.starts_at)} {occurrence.title}
      </span>
    </div>
  )
}

export function CalendarPage() {
  const c = useCalendarPageController()
  const move = useCalendarEventMove(c.calendars)
  const isAdmin = useAuthStore((s) => s.user?.is_portal_admin ?? false)
  const suppressGridClickRef = useRef(false)
  const [draggedEvent, setDraggedEvent] = useState<PortalCalendarOccurrence | null>(null)
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 8 } }))
  const { activeSelected, activeEditOpen } = c
  const narrowViewport = useNarrowViewport()
  const tourActive = useGuidedTourActive()
  const [calendarsOpen, setCalendarsOpen] = useState(false)
  const calendarsPanelId = useId()
  const calendarsPanelOpen = !narrowViewport || calendarsOpen || tourActive

  function armClickSuppress() {
    suppressGridClickRef.current = true
    window.setTimeout(() => {
      suppressGridClickRef.current = false
    }, 0)
  }

  function onEventDragStart(event: DragStartEvent) {
    setDraggedEvent(draggedOccurrence(event.active.data))
  }

  function onEventDragEnd(event: DragEndEvent) {
    armClickSuppress()
    setDraggedEvent(null)
    const occ = draggedOccurrence(event.active.data)
    if (!occ || !event.over) return
    const day = parseCalendarDayDropId(String(event.over.id))
    if (!day) return
    move.moveToDay(occ, day)
  }

  function onEventDragCancel() {
    armClickSuppress()
    setDraggedEvent(null)
  }

  return (
    <div className={styles.page}>
      <div className={narrow.calendarsBlock}>
        <button
          type="button"
          className={narrow.calendarsToggle}
          aria-expanded={calendarsPanelOpen}
          aria-controls={calendarsPanelId}
          onClick={() => setCalendarsOpen((open) => !open)}
        >
          Календари
        </button>
        <div
          id={calendarsPanelId}
          className={`${narrow.calendarsPanel}${calendarsPanelOpen ? ` ${narrow.calendarsPanelOpen}` : ''}`}
        >
          <div
            className={narrow.calendarsPanelInner}
            inert={narrowViewport && !calendarsPanelOpen ? true : undefined}
          >
            <CalendarSidebar
              calendars={c.calendars}
              activeIds={c.activeIds}
              peerViewActive={Boolean(c.peerUserSub)}
              onToggle={c.toggleCal}
              onUpdate={(id, patch) => c.updateCalMut.mutate({ id, patch })}
              onCreate={() => c.createCalMut.mutate()}
              onDelete={(id) => c.deleteCalMut.mutate(id)}
              updatePending={c.updateCalMut.isPending}
              createPending={c.createCalMut.isPending}
              deletePending={c.deleteCalMut.isPending}
            />
          </div>
        </div>
      </div>
      <section className={styles.main}>
        <div className={`${styles.toolbar} ${narrow.toolbar}`} data-tour="calendar-toolbar">
          <div className={`${styles.toolbarLeft} ${narrow.toolbarLeft}`}>
            <button type="button" className="btn-secondary" onClick={() => c.moveCursor(new Date())}>
              Сегодня
            </button>
            <button
              type="button"
              className="btn-secondary"
              onClick={() =>
                c.moveCursor(new Date(c.cursor.getFullYear(), c.cursor.getMonth() - 1, 1))
              }
            >
              ‹
            </button>
            <span className={`${styles.monthLabel} ${narrow.monthLabel}`}>{c.monthTitle}</span>
            <button
              type="button"
              className="btn-secondary"
              onClick={() =>
                c.moveCursor(new Date(c.cursor.getFullYear(), c.cursor.getMonth() + 1, 1))
              }
            >
              ›
            </button>
          </div>
          <div className={`${styles.toolbarRight} ${narrow.toolbarRight}`}>
            <CalendarAdminTools
              onPickPerson={(sub) => c.setPeerUserSub(sub)}
              onDepartmentChange={() => c.setPeerUserSub(null)}
              onClearPerson={() => c.setPeerUserSub(null)}
            />
            {isAdmin ? null : (
              <div className={`${styles.peerPicker} ${narrow.peerPicker}`} data-tour="calendar-peer-picker">
                <UserPicker
                  value={c.peerUserSub ?? ''}
                  onChange={(sub) => c.setPeerUserSub(sub || null)}
                  placeholder="Календарь участника…"
                />
              </div>
            )}
            <CalendarEventSearchField onSelect={c.onSearchSelect} />
            <button
              type="button"
              className={`btn-primary ${styles.createEventBtn} ${narrow.createEventBtn}`}
              data-tour="calendar-create-event"
              disabled={
                Boolean(c.peerUserSub) && (c.peerContextPending || c.peerContextError)
              }
              onClick={() => c.openCreate()}
            >
              Создать событие
            </button>
          </div>
        </div>

        {c.pageError ? (
          <p className="text-danger" role="alert">
            {c.pageError}
          </p>
        ) : null}

        <DndContext
          sensors={sensors}
          collisionDetection={pointerWithin}
          onDragStart={onEventDragStart}
          onDragEnd={onEventDragEnd}
          onDragCancel={onEventDragCancel}
        >
          <div
            className={`${styles.gridFrame}${c.expandedDayKey ? ` ${styles.gridFrameExpanded}` : ''}`}
          >
            <div
              className={`${styles.grid}${c.expandedDayKey ? ` ${styles.gridHasExpanded}` : ''} ${narrow.grid}`}
              role="grid"
              aria-label="Календарь на месяц"
              data-tour="calendar-grid"
            >
            {WEEKDAYS.map((w) => (
              <div key={w} className={styles.weekday}>
                {w}
              </div>
            ))}
            {c.cells.map((day) => {
              const key = day.toDateString()
              const events = c.byDay.get(key) ?? []
              const isToday = key === new Date().toDateString()
              const outside = day.getMonth() !== c.cursor.getMonth()
              return (
                <CalendarDayCell
                  key={key}
                  day={day}
                  events={events}
                  isToday={isToday}
                  outside={outside}
                  highlightEvent={c.highlightEvent}
                  expanded={c.expandedDayKey === key}
                  onExpand={() => c.setExpandedDayKey(key)}
                  onCollapse={() => c.setExpandedDayKey(null)}
                  onOpenCreate={c.openCreate}
                  onSelectEvent={(occ: PortalCalendarOccurrence) => {
                    c.setDetailActionError(null)
                    c.setSelected(occ)
                  }}
                  canDragEvent={move.canDragOccurrence}
                  suppressGridClickRef={suppressGridClickRef}
                  narrow={narrowViewport}
                />
              )
            })}
            </div>
          </div>
          <DragOverlay style={{ zIndex: 'var(--z-floating)' }} dropAnimation={null}>
            {draggedEvent ? <DraggedEventChip occurrence={draggedEvent} /> : null}
          </DragOverlay>
        </DndContext>
      </section>

      {c.formOpen ? (
        <CalendarEventFormModal
          calendars={c.calendars}
          initialCalendarId={c.draftCalendarId}
          startsLocal={c.draftStarts}
          endsLocal={c.draftEnds}
          pending={c.createMut.isPending}
          peerCreateForSub={c.peerUserSub}
          peerCalendarLabel={c.peerUserSub ? 'Календарь выбранного участника' : null}
          submitError={c.formSubmitError}
          onClearSubmitError={() => c.setFormSubmitError(null)}
          onClose={() => {
            c.setFormOpen(false)
            c.setFormSubmitError(null)
          }}
          onSubmit={(payload) => c.createMut.mutate(payload)}
        />
      ) : null}

      {activeEditOpen && activeSelected ? (
        <CalendarEventFormModal
          calendars={c.calendars}
          initialCalendarId={activeSelected.calendar_id}
          startsLocal=""
          endsLocal=""
          mode="edit"
          initialOccurrence={activeSelected}
          pending={c.updateMut.isPending}
          submitError={c.editSubmitError}
          tourDemo={c.tourEdit}
          onClearSubmitError={() => c.setEditSubmitError(null)}
          onClose={() => {
            c.setEditOpen(false)
            c.setEditSubmitError(null)
            if (c.tourEdit || c.highlightEvent) {
              const next = new URLSearchParams(c.params)
              next.delete('edit')
              c.setParams(next, { replace: true })
            }
          }}
          onSubmitEdit={(patch) =>
            c.updateMut.mutate({
              id: activeSelected.event_id,
              calendarId: activeSelected.calendar_id,
              body: patch,
            })
          }
        />
      ) : null}

      {activeSelected && !activeEditOpen ? (
        <CalendarEventDetailModal
          occurrence={activeSelected}
          deletePending={false}
          canEdit={Boolean(c.canEditSelected)}
          actionError={c.detailActionError}
          onClose={() => {
            c.setSelected(null)
            c.setQueryOpenedEventId(null)
            c.setDetailActionError(null)
            if (c.highlightEvent) {
              const next = new URLSearchParams(c.params)
              next.delete('event')
              next.delete('edit')
              c.setParams(next, { replace: true })
            }
          }}
          onDelete={() => c.scheduleEventDelete(activeSelected)}
          onEdit={() => {
            c.setDetailActionError(null)
            c.setEditSubmitError(null)
            if (c.highlightEvent) {
              const next = new URLSearchParams(c.params)
              next.set('edit', '1')
              c.setParams(next, { replace: true })
            } else {
              c.setEditOpen(true)
            }
          }}
        />
      ) : null}
    </div>
  )
}
