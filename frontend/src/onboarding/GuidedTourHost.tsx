import { useEffect, useMemo, useRef } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useLocation } from 'react-router'

import {
  ACCOUNT_PREFERENCES_QUERY_KEY,
  getAccountPreferences,
  patchAccountPreferences,
} from '../api/accountApi'
import { isTimesheetOnlyUser, isUserManagerOrAdmin } from '../domain/auth/authRoles'
import {
  canShowContextualTourHints,
  canSkipEntireGuidedTour,
  shouldAutoStartGuidedTour,
} from '../domain/onboarding/guidedTour'
import {
  resolveLocationTourPageId,
  shouldClearHintFreeze,
  shouldStartContextualHint,
  tourLocationKey,
  unseenStepsForPage,
} from '../domain/onboarding/guidedTourPages'
import { useNotifyToast } from '../hooks/useNotifyToast'
import { useAuthStore } from '../store/authStore'
import { userFacingMessageFromUnknown } from '../utils/apiUserMessage'
import { readGuidedTourSeenStepIds } from './guidedTourSeenStorage'
import { resolveGuidedTourSteps } from './steps'
import { TourEngine } from './TourEngine'
import { useTourStore } from './tourStore'

export function GuidedTourHost() {
  const qc = useQueryClient()
  const location = useLocation()
  const user = useAuthStore((s) => s.user)
  const phase = useTourStore((s) => s.phase)
  const openWelcome = useTourStore((s) => s.openWelcome)
  const startHint = useTourStore((s) => s.startHint)
  const setHintFrozenLocationKeys = useTourStore((s) => s.setHintFrozenLocationKeys)
  const startedRef = useRef(false)
  const notify = useNotifyToast()

  const timesheetOnly = user
    ? isTimesheetOnlyUser(user)
    : false

  const ctx = useMemo(
    () => ({
      isPortalAdmin: Boolean(user?.is_portal_admin),
      isManagerOrAdmin: user
        ? isUserManagerOrAdmin(user)
        : false,
      isTimesheetOnly: timesheetOnly,
    }),
    [user, timesheetOnly],
  )

  const canSkipEntire = canSkipEntireGuidedTour(ctx)

  const prefsQ = useQuery({
    queryKey: ACCOUNT_PREFERENCES_QUERY_KEY,
    queryFn: getAccountPreferences,
    enabled: Boolean(user),
    staleTime: 60_000,
  })

  const completeMut = useMutation({
    mutationFn: () => patchAccountPreferences({ guided_tour_completed: true }),
    onSuccess: (data) => {
      qc.setQueryData(ACCOUNT_PREFERENCES_QUERY_KEY, data)
    },
    onError: (error) => notify(userFacingMessageFromUnknown(error)),
  })

  useEffect(() => {
    if (!user) return
    if (!prefsQ.isSuccess || !prefsQ.data) return
    if (startedRef.current) return
    if (phase !== 'idle') return
    if (!shouldAutoStartGuidedTour(prefsQ.data.guided_tour_completed)) return
    startedRef.current = true
    openWelcome(resolveGuidedTourSteps(ctx))
  }, [user, prefsQ.isSuccess, prefsQ.data, phase, ctx, openWelcome])

  useEffect(() => {
    if (!user) return
    if (!prefsQ.isSuccess || !prefsQ.data?.guided_tour_completed) return
    if (!canShowContextualTourHints(ctx)) return
    if (phase !== 'idle') return
    const locationKey = tourLocationKey(location.pathname, location.search)
    const frozen = useTourStore.getState().hintFrozenLocationKeys
    if (shouldClearHintFreeze(frozen, locationKey)) {
      setHintFrozenLocationKeys([])
    }
    const pageId = resolveLocationTourPageId(location.pathname, location.search)
    const unseen = pageId
      ? unseenStepsForPage(
          resolveGuidedTourSteps(ctx),
          readGuidedTourSeenStepIds(user.sub),
          pageId,
        )
      : []
    if (
      !shouldStartContextualHint({
        tourCompleted: prefsQ.data.guided_tour_completed,
        canShowHints: canShowContextualTourHints(ctx),
        phase,
        locationKey,
        frozenLocationKeys: shouldClearHintFreeze(frozen, locationKey) ? [] : frozen,
        unseenCount: unseen.length,
      })
    ) {
      return
    }
    startHint(unseen)
  }, [
    user,
    prefsQ.isSuccess,
    prefsQ.data?.guided_tour_completed,
    ctx,
    phase,
    location.pathname,
    location.search,
    startHint,
    setHintFrozenLocationKeys,
  ])

  if (!user) return null

  return (
    <TourEngine
      canSkipEntire={canSkipEntire}
      tourVariant={timesheetOnly ? 'timesheet' : 'full'}
      onComplete={() => {
        startedRef.current = true
        completeMut.mutate()
      }}
    />
  )
}
