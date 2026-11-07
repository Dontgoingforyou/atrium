import { useDraggable, useDroppable } from '@dnd-kit/core'
import { useEffect, useRef, useState } from 'react'

import { calendarDayDropId, calendarOccurrenceDragId } from '../../domain/calendar/occurrenceDayMove'
import { formatTime } from '../../domain/calendar/calendarRrule'
import { contrastingTextOn } from '../../utils/color/contrastingTextOn'
import { useClickOutside } from '../../hooks/useClickOutside'
import { TOUR_DEMO_EVENT_TITLE } from '../../onboarding/ensureTourDemoEvent'
import type { PortalCalendarOccurrence } from '../../types/calendar'
import { maxVisibleChips } from './calendarDayCellLayout'
import styles from '@/styles/modules/calendar/CalendarPage.module.css'
import narrow from '@/styles/modules/calendar/CalendarPageNarrow.module.css'

type Props = {
  day: Date
  events: PortalCalendarOccurrence[]
  isToday: boolean
  outside: boolean
  highlightEvent: string | null
  expanded: boolean
  onExpand: () => void
  onCollapse: () => void
  onOpenCreate: (day: Date) => void
  onSelectEvent: (occ: PortalCalendarOccurrence) => void
  canDragEvent: (occ: PortalCalendarOccurrence) => boolean
  suppressGridClickRef: { current: boolean }
  narrow?: boolean
}

function eventsWordRu(n: number): string {
  const abs = Math.abs(n) % 100
  const last = abs % 10
  if (abs > 10 && abs < 20) return 'событий'
  if (last === 1) return 'событие'
  if (last >= 2 && last <= 4) return 'события'
  return 'событий'
}

function EventChip({
  occ,
  highlightEvent,
  onSelectEvent,
  canDrag,
  suppressGridClickRef,
  isTourAnchor = false,
}: {
  occ: PortalCalendarOccurrence
  highlightEvent: string | null
  onSelectEvent: (occ: PortalCalendarOccurrence) => void
  canDrag: boolean
  suppressGridClickRef: { current: boolean }
  isTourAnchor?: boolean
}) {
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
    id: calendarOccurrenceDragId(occ.event_id, occ.original_start),
    data: { occurrence: occ },
    disabled: !canDrag,
  })
  const background = occ.color || occ.calendar_color
  return (
    <button
      type="button"
      ref={setNodeRef}
      className={`${styles.eventChip} ${narrow.eventChip}${
        highlightEvent === occ.event_id ? ` ${styles.eventChipHighlight}` : ''
      }${occ.is_peer_view ? ` ${styles.eventChipPeer}` : ''}${
        canDrag ? ` ${styles.eventChipDraggable}` : ''
      }${isDragging ? ` ${styles.eventChipDragging}` : ''}`}
      style={{ background, color: contrastingTextOn(background) }}
      {...(canDrag ? { ...attributes, ...listeners } : {})}
      onClick={(ev) => {
        ev.stopPropagation()
        if (suppressGridClickRef.current) {
          suppressGridClickRef.current = false
          return
        }
        onSelectEvent(occ)
      }}
      title={`${formatTime(occ.starts_at)} ${occ.title}`}
      {...(isTourAnchor ? { 'data-tour': 'calendar-event' } : {})}
    >
      <span className={styles.eventChipLabel}>
        {formatTime(occ.starts_at)} {occ.title}
      </span>
    </button>
  )
}

export function CalendarDayCell({
  day,
  events,
  isToday,
  outside,
  highlightEvent,
  expanded,
  onExpand,
  onCollapse,
  onOpenCreate,
  onSelectEvent,
  canDragEvent,
  suppressGridClickRef,
  narrow: narrowViewport = false,
}: Props) {
  const { setNodeRef: setDropRef, isOver } = useDroppable({ id: calendarDayDropId(day) })
  const wrapRef = useRef<HTMLDivElement>(null)
  const eventsRef = useRef<HTMLDivElement>(null)
  const [eventsHeight, setEventsHeight] = useState(0)
  useClickOutside(expanded, [wrapRef], onCollapse, 'mousedown')

  useEffect(() => {
    const el = eventsRef.current
    if (!el) return
    const apply = () => {
      const next = Math.round(el.clientHeight)
      setEventsHeight((prev) => (Math.abs(next - prev) >= 2 ? next : prev))
    }
    apply()
    const ro = new ResizeObserver(apply)
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  const collapsedLimit = maxVisibleChips(eventsHeight, events.length)
  const orderedEvents = (() => {
    const tourIdx = events.findIndex((e) => e.title === TOUR_DEMO_EVENT_TITLE)
    if (tourIdx <= 0) return events
    return [events[tourIdx]!, ...events.filter((_, i) => i !== tourIdx)]
  })()
  const head = orderedEvents.slice(0, collapsedLimit)
  const rest = orderedEvents.slice(collapsedLimit)
  const hiddenCount = rest.length

  return (
    <div
      ref={wrapRef}
      className={styles.dayCellWrap}
      {...(isToday ? { 'data-tour': 'calendar-day-cell' } : {})}
    >
      <div
        ref={setDropRef}
        className={[
          styles.dayCell,
          narrow.dayCell,
          outside ? styles.dayOutside : '',
          expanded ? styles.dayCellExpanded : '',
          expanded ? narrow.dayCellExpanded : '',
          isOver ? styles.dayCellDragOver : '',
        ]
          .filter(Boolean)
          .join(' ')}
        onClick={() => {
          if (suppressGridClickRef.current) {
            suppressGridClickRef.current = false
            return
          }
          if (expanded) return
          if (narrowViewport && events.length > 0) onExpand()
          else onOpenCreate(day)
        }}
        onKeyDown={(ev) => {
          if (expanded || (ev.key !== 'Enter' && ev.key !== ' ')) return
          ev.preventDefault()
          if (narrowViewport && events.length > 0) onExpand()
          else onOpenCreate(day)
        }}
        role="gridcell"
        tabIndex={0}
      >
        <div className={styles.dayNumRow}>
          <div className={styles.dayNum}>
            {isToday ? <span className={styles.dayNumToday}>{day.getDate()}</span> : day.getDate()}
          </div>
          {expanded ? (
            <button
              type="button"
              className={styles.dayCollapseBtn}
              title="Свернуть"
              aria-label="Свернуть день"
              onClick={(e) => {
                e.stopPropagation()
                onCollapse()
              }}
            >
              ✕
            </button>
          ) : null}
        </div>
        <div ref={eventsRef} className={`${styles.dayEvents} ${narrow.dayEvents}`}>
          {head.map((occ) => (
            <EventChip
              key={`${occ.event_id}-${occ.original_start}`}
              occ={occ}
              highlightEvent={highlightEvent}
              onSelectEvent={onSelectEvent}
              canDrag={canDragEvent(occ)}
              suppressGridClickRef={suppressGridClickRef}
              isTourAnchor={occ.title === TOUR_DEMO_EVENT_TITLE}
            />
          ))}
          {hiddenCount > 0 ? (
            <>
              <div
                className={styles.dayExtraSlot}
                data-state={expanded ? 'open' : 'closed'}
              >
                {expanded ? (
                  <div className={styles.dayExtraInner}>
                    {rest.map((occ) => (
                      <EventChip
                        key={`${occ.event_id}-${occ.original_start}`}
                        occ={occ}
                        highlightEvent={highlightEvent}
                        onSelectEvent={onSelectEvent}
                        canDrag={canDragEvent(occ)}
                        suppressGridClickRef={suppressGridClickRef}
                        isTourAnchor={occ.title === TOUR_DEMO_EVENT_TITLE}
                      />
                    ))}
                  </div>
                ) : null}
              </div>
              <button
                type="button"
                className={`${styles.dayMore} ${narrow.dayMore}`}
                aria-expanded={expanded}
                onClick={(e) => {
                  e.stopPropagation()
                  if (expanded) onCollapse()
                  else onExpand()
                }}
              >
                {expanded ? 'Свернуть' : `+${hiddenCount} ${eventsWordRu(hiddenCount)}`}
              </button>
            </>
          ) : null}
        </div>
      </div>
    </div>
  )
}
