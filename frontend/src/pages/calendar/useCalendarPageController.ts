import { useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useSearchParams } from 'react-router'

import {
  createCalendar,
  createEvent,
  deleteCalendar,
  deleteEvent,
  getEvent,
  getPeerCalendarContext,
  listCalendars,
  listOccurrences,
  updateCalendar,
  updateEventWithCas,
} from '../../api/calendar/calendarApi'
import { DEFAULT_CALENDAR_COLOR } from '../../domain/calendar/calendarColor'
import { eventToOccurrence } from '../../domain/calendar/calendarEventToOccurrence'
import { toLocalInput } from '../../domain/calendar/calendarLocalTime'
import {
  addDays,
  endOfMonth,
  startOfMonth,
  startOfWeek,
  toIso,
} from '../../domain/calendar/calendarRrule'
import { useScheduleDeleteWithUndo } from '../../hooks/useScheduleDeleteWithUndo'
import type {
  CalendarEventPatch,
  CalendarEventSearchHit,
  PortalCalendarOccurrence,
} from '../../types/calendar'
import { userFacingMessageFromUnknown } from '../../utils/apiUserMessage'
import { invalidatePortalSearchQueries } from '@/utils/search/invalidatePortalSearch'
import { isApiConflictError } from '../../api/apiConflict'
import { useAuthStore } from '../../store/authStore'
import { canEditCalendarOccurrence, defaultOwnCalendarId, ownCalendars } from './calendarOwn'
import { calendarQueryKeys } from './calendarQueryKeys'
import { useCalendarWebSocket } from './useCalendarWebSocket'

export type CalendarPageController = ReturnType<typeof useCalendarPageController>

export function useCalendarPageController() {
  const qc = useQueryClient()
  const currentUserSub = useAuthStore((s) => s.user?.sub ?? null)
  const scheduleDeleteWithUndo = useScheduleDeleteWithUndo()
  const [params, setParams] = useSearchParams()
  const highlightEvent = params.get('event')
  const highlightCalendar = params.get('calendar')
  const tourEdit = params.get('edit') === '1'

  useCalendarWebSocket(true)

  const [cursor, setCursor] = useState(() => new Date())
  const [enabledCalIds, setEnabledCalIds] = useState<Set<string> | null>(null)
  const [formOpen, setFormOpen] = useState(false)
  const [editOpen, setEditOpen] = useState(false)
  const [selected, setSelected] = useState<PortalCalendarOccurrence | null>(null)
  const [pageError, setPageError] = useState<string | null>(null)
  const [formSubmitError, setFormSubmitError] = useState<string | null>(null)
  const [editSubmitError, setEditSubmitError] = useState<string | null>(null)
  const [detailActionError, setDetailActionError] = useState<string | null>(null)
  const [draftStarts, setDraftStarts] = useState('')
  const [draftEnds, setDraftEnds] = useState('')
  const [draftCalendarId, setDraftCalendarId] = useState('')
  const [peerUserSub, setPeerUserSub] = useState<string | null>(null)
  /** Раскрытая ячейка дня (toDateString) — все события поверх сетки */
  const [expandedDayKey, setExpandedDayKey] = useState<string | null>(null)
  /** Id события, открытого из ?event= (уведомление / тур). */
  const [queryOpenedEventId, setQueryOpenedEventId] = useState<string | null>(null)
  const hideQueryModal = queryOpenedEventId !== null && highlightEvent === null
  const fromQueryActive =
    queryOpenedEventId !== null && highlightEvent === queryOpenedEventId
  const activeSelected = hideQueryModal ? null : selected
  const activeEditOpen = hideQueryModal ? false : fromQueryActive ? tourEdit : editOpen

  const rangeStart = startOfWeek(startOfMonth(cursor))
  const rangeEnd = addDays(startOfWeek(endOfMonth(cursor)), 7)

  function moveCursor(next: Date) {
    setExpandedDayKey(null)
    setCursor(next)
  }

  const calendarsQuery = useQuery({
    queryKey: calendarQueryKeys.calendars,
    queryFn: listCalendars,
  })

  const peerContextQuery = useQuery({
    queryKey: calendarQueryKeys.peerContext(peerUserSub ?? ''),
    queryFn: () => getPeerCalendarContext(peerUserSub!),
    enabled: Boolean(peerUserSub),
  })

  const activeIds = useMemo(() => {
    const owned = ownCalendars(calendarsQuery.data ?? [])
    if (enabledCalIds) return [...enabledCalIds].filter((id) => owned.some((calendar) => calendar.id === id))
    if (highlightCalendar && owned.some((calendar) => calendar.id === highlightCalendar)) {
      return [highlightCalendar]
    }
    return owned.map((calendar) => calendar.id)
  }, [calendarsQuery.data, enabledCalIds, highlightCalendar])

  const occurrencesQuery = useQuery({
    queryKey: calendarQueryKeys.occurrences(
      toIso(rangeStart),
      toIso(rangeEnd),
      peerUserSub ? [] : activeIds,
      peerUserSub,
    ),
    queryFn: () =>
      listOccurrences({
        from: toIso(rangeStart),
        to: toIso(rangeEnd),
        calendarIds: peerUserSub ? [] : activeIds,
        userSub: peerUserSub,
      }),
    enabled: Boolean(peerUserSub) || activeIds.length > 0,
  })

  // Сброс после скрытия deeplink/тур-модалки (отложенно — lint set-state-in-effect).
  useEffect(() => {
    if (!hideQueryModal) return
    const timer = window.setTimeout(() => {
      setSelected(null)
      setEditOpen(false)
      setQueryOpenedEventId(null)
      setDetailActionError(null)
      setEditSubmitError(null)
    }, 0)
    return () => window.clearTimeout(timer)
  }, [hideQueryModal])

  // ?event= из уведомления / поиска / тура — открыть модалку для нового id
  useEffect(() => {
    if (!highlightEvent || formOpen) return
    if (queryOpenedEventId === highlightEvent) return

    let cancelled = false
    const openOcc = (occ: PortalCalendarOccurrence) => {
      if (cancelled) return
      setQueryOpenedEventId(highlightEvent)
      setSelected(occ)
      setDetailActionError(null)
    }

    const fromGrid = (occurrencesQuery.data ?? []).find((o) => o.event_id === highlightEvent)
    if (fromGrid) {
      const timer = window.setTimeout(() => openOcc(fromGrid), 0)
      return () => {
        cancelled = true
        window.clearTimeout(timer)
      }
    }

    void getEvent(highlightEvent)
      .then((ev) => {
        if (cancelled) return
        const starts = new Date(ev.starts_at)
        moveCursor(new Date(starts.getFullYear(), starts.getMonth(), 1))
        openOcc(eventToOccurrence(ev, calendarsQuery.data ?? []))
      })
      .catch((e: unknown) => {
        if (!cancelled) setPageError(userFacingMessageFromUnknown(e))
      })
    return () => {
      cancelled = true
    }
  }, [highlightEvent, occurrencesQuery.data, calendarsQuery.data, formOpen, queryOpenedEventId])

  const createMut = useMutation({
    mutationFn: createEvent,
    onSuccess: async () => {
      setFormOpen(false)
      setFormSubmitError(null)
      await qc.invalidateQueries({ queryKey: calendarQueryKeys.all })
      invalidatePortalSearchQueries(qc)
    },
    onError: (e) => setFormSubmitError(userFacingMessageFromUnknown(e)),
  })

  const updateMut = useMutation({
    mutationFn: ({
      id,
      body,
      calendarId,
    }: {
      id: string
      calendarId?: string
      body: Omit<CalendarEventPatch, 'expected_version'>
    }) => updateEventWithCas(id, body, undefined, calendarId),
    onSuccess: async () => {
      setEditOpen(false)
      setSelected(null)
      setEditSubmitError(null)
      await qc.invalidateQueries({ queryKey: calendarQueryKeys.all })
      invalidatePortalSearchQueries(qc)
    },
    onError: (e) => {
      setEditSubmitError(userFacingMessageFromUnknown(e))
      if (isApiConflictError(e)) {
        void qc.invalidateQueries({ queryKey: calendarQueryKeys.all })
      }
    },
  })

  const updateCalMut = useMutation({
    mutationFn: ({
      id,
      patch,
    }: {
      id: string
      patch: { title?: string; color?: string }
    }) => updateCalendar(id, patch),
    onSuccess: async (_data, vars) => {
      setPageError(null)
      await qc.invalidateQueries({ queryKey: calendarQueryKeys.all })
      if (vars.patch.color) {
        const color = vars.patch.color
        qc.setQueriesData<PortalCalendarOccurrence[]>(
          { queryKey: calendarQueryKeys.occurrencesRoot },
          (prev) =>
            prev?.map((occ) =>
              occ.calendar_id === vars.id ? { ...occ, calendar_color: color } : occ,
            ),
        )
      }
    },
    onError: (e) => setPageError(userFacingMessageFromUnknown(e)),
  })

  const createCalMut = useMutation({
    mutationFn: () =>
      createCalendar({
        title: 'Новый календарь',
        color: DEFAULT_CALENDAR_COLOR,
      }),
    onSuccess: async (created) => {
      setPageError(null)
      setEnabledCalIds((prev) => (prev ? new Set([...prev, created.id]) : prev))
      await qc.invalidateQueries({ queryKey: calendarQueryKeys.calendars })
    },
    onError: (e) => setPageError(userFacingMessageFromUnknown(e)),
  })

  const deleteCalMut = useMutation({
    mutationFn: (id: string) => deleteCalendar(id),
    onSuccess: async (_data, id) => {
      setPageError(null)
      setEnabledCalIds((prev) => {
        if (!prev || !prev.has(id)) return prev
        const next = new Set(prev)
        next.delete(id)
        return next
      })
      await qc.invalidateQueries({ queryKey: calendarQueryKeys.all })
    },
    onError: (e) => setPageError(userFacingMessageFromUnknown(e)),
  })

  function openCreate(day?: Date) {
    const base = day ?? new Date()
    const start = new Date(base)
    start.setHours(10, 0, 0, 0)
    const end = new Date(base)
    end.setHours(11, 0, 0, 0)
    setDraftStarts(toLocalInput(start))
    setDraftEnds(toLocalInput(end))
    if (peerUserSub) {
      if (peerContextQuery.isError) {
        setPageError(userFacingMessageFromUnknown(peerContextQuery.error))
        return
      }
      if (!peerContextQuery.data) {
        void peerContextQuery.refetch()
        return
      }
      setDraftCalendarId(peerContextQuery.data.calendar_id)
    } else {
      setDraftCalendarId(defaultOwnCalendarId(calendarsQuery.data ?? []))
    }
    setFormSubmitError(null)
    setFormOpen(true)
  }

  function toggleCal(id: string) {
    const current = new Set(activeIds)
    if (current.has(id)) current.delete(id)
    else current.add(id)
    setEnabledCalIds(current)
  }

  function onSearchSelect(hit: CalendarEventSearchHit) {
    const starts = new Date(hit.starts_at)
    moveCursor(new Date(starts.getFullYear(), starts.getMonth(), 1))
    const next = new URLSearchParams(params)
    next.set('event', hit.id)
    setParams(next, { replace: true })
  }

  function scheduleEventDelete(occ: PortalCalendarOccurrence) {
    const eventId = occ.event_id
    const snapshots = qc.getQueriesData<PortalCalendarOccurrence[]>({
      queryKey: calendarQueryKeys.occurrencesRoot,
    })
    setSelected(null)
    setQueryOpenedEventId(null)
    setDetailActionError(null)
    scheduleDeleteWithUndo({
      message: 'Событие удалено',
      optimistic: () => {
        qc.setQueriesData<PortalCalendarOccurrence[]>(
          { queryKey: calendarQueryKeys.occurrencesRoot },
          (prev) => prev?.filter((o) => o.event_id !== eventId),
        )
      },
      revert: () => {
        for (const [key, data] of snapshots) {
          if (data) qc.setQueryData(key, data)
        }
      },
      commit: () => {
        void deleteEvent(eventId, occ.calendar_id)
          .then(() => {
            void qc.invalidateQueries({ queryKey: calendarQueryKeys.all })
            invalidatePortalSearchQueries(qc)
          })
          .catch((e: unknown) => {
            for (const [key, data] of snapshots) {
              if (data) qc.setQueryData(key, data)
            }
            setPageError(userFacingMessageFromUnknown(e))
          })
      },
    })
  }

  const byDay = useMemo(() => {
    const map = new Map<string, PortalCalendarOccurrence[]>()
    for (const occ of occurrencesQuery.data ?? []) {
      const key = new Date(occ.starts_at).toDateString()
      const list = map.get(key) ?? []
      list.push(occ)
      map.set(key, list)
    }
    return map
  }, [occurrencesQuery.data])

  const cells = useMemo(() => {
    const list: Date[] = []
    for (let d = new Date(rangeStart); d < rangeEnd; d = addDays(d, 1)) {
      list.push(new Date(d))
    }
    return list
  }, [rangeStart, rangeEnd])

  const monthTitle = cursor.toLocaleDateString('ru-RU', { month: 'long', year: 'numeric' })
  const calendars = calendarsQuery.data ?? []
  const selectedCal = activeSelected
    ? calendars.find((c) => c.id === activeSelected.calendar_id)
    : null
  const canEditSelected = canEditCalendarOccurrence(
    activeSelected,
    currentUserSub,
    selectedCal?.my_role,
  )

  return {
    // query params
    highlightEvent,
    tourEdit,
    params,
    setParams,
    // navigation
    cursor,
    moveCursor,
    monthTitle,
    cells,
    byDay,
    // calendars
    calendars,
    activeIds,
    toggleCal,
    updateCalMut,
    createCalMut,
    deleteCalMut,
    onSearchSelect,
    // peer view
    peerUserSub,
    setPeerUserSub,
    peerContextPending: peerContextQuery.isPending,
    peerContextError: peerContextQuery.isError,
    // selection / modals
    activeSelected,
    activeEditOpen,
    expandedDayKey,
    setExpandedDayKey,
    setSelected,
    setDetailActionError,
    // create form
    formOpen,
    setFormOpen,
    draftStarts,
    draftEnds,
    draftCalendarId,
    openCreate,
    createMut,
    formSubmitError,
    setFormSubmitError,
    // edit form
    updateMut,
    editSubmitError,
    setEditSubmitError,
    setEditOpen,
    // detail
    canEditSelected,
    detailActionError,
    setQueryOpenedEventId,
    scheduleEventDelete,
    // page error
    pageError,
  }
}
