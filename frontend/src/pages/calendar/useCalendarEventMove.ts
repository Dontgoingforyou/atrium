import { useCallback, useRef } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'

import { overrideEventOccurrence, updateEventWithCas } from '../../api/calendar/calendarApi'
import {
  applyOccurrenceDayMove,
  planOccurrenceDayMove,
  type OccurrenceDayMove,
} from '../../domain/calendar/occurrenceDayMove'
import { useNotifyToast } from '../../hooks/useNotifyToast'
import { useAuthStore } from '../../store/authStore'
import type { PortalCalendar, PortalCalendarOccurrence } from '../../types/calendar'
import { userFacingMessageFromUnknown } from '../../utils/apiUserMessage'
import { invalidatePortalSearchQueries } from '@/utils/search/invalidatePortalSearch'
import { canDragCalendarOccurrence } from './calendarOwn'
import { calendarQueryKeys } from './calendarQueryKeys'

async function saveOccurrenceDayMove(move: OccurrenceDayMove): Promise<void> {
  if (move.kind === 'patch') {
    await updateEventWithCas(
      move.event_id,
      {
        starts_at: move.starts_at,
        ends_at: move.ends_at,
      },
      undefined,
      move.calendar_id,
    )
    return
  }
  await overrideEventOccurrence(
    move.event_id,
    {
      original_start: move.original_start,
      starts_at: move.starts_at,
      ends_at: move.ends_at,
      title: move.title,
      description: move.description,
      location: move.location,
      is_cancelled: false,
    },
    move.calendar_id,
  )
}

export function useCalendarEventMove(calendars: PortalCalendar[]) {
  const qc = useQueryClient()
  const notify = useNotifyToast()
  const currentUserSub = useAuthStore((s) => s.user?.sub ?? null)
  const moving = useRef(false)

  const canDragOccurrence = useCallback(
    (occurrence: PortalCalendarOccurrence) => {
      const role = calendars.find((calendar) => calendar.id === occurrence.calendar_id)?.my_role
      return canDragCalendarOccurrence(occurrence, currentUserSub, role)
    },
    [calendars, currentUserSub],
  )

  const moveMut = useMutation({
    mutationFn: saveOccurrenceDayMove,
    onMutate: async (move) => {
      await qc.cancelQueries({ queryKey: calendarQueryKeys.occurrencesRoot })
      const snapshots = qc.getQueriesData<PortalCalendarOccurrence[]>({
        queryKey: calendarQueryKeys.occurrencesRoot,
      })
      qc.setQueriesData<PortalCalendarOccurrence[]>(
        { queryKey: calendarQueryKeys.occurrencesRoot },
        (prev) => (prev ? applyOccurrenceDayMove(prev, move) : prev),
      )
      return { snapshots }
    },
    onError: (error, _move, context) => {
      for (const [key, data] of context?.snapshots ?? []) {
        qc.setQueryData(key, data)
      }
      notify(userFacingMessageFromUnknown(error), { tone: 'error' })
      void qc.invalidateQueries({ queryKey: calendarQueryKeys.occurrencesRoot })
    },
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: calendarQueryKeys.occurrencesRoot })
      invalidatePortalSearchQueries(qc)
    },
    onSettled: () => {
      moving.current = false
    },
  })

  const moveToDay = useCallback(
    (occurrence: PortalCalendarOccurrence, targetDay: Date) => {
      if (moving.current || !canDragOccurrence(occurrence)) return
      const plan = planOccurrenceDayMove(occurrence, targetDay)
      if (!plan) return
      moving.current = true
      moveMut.mutate(plan)
    },
    [canDragOccurrence, moveMut],
  )

  return { canDragOccurrence, moveToDay }
}
