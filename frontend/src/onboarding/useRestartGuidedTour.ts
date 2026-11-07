import { useMutation, useQueryClient } from '@tanstack/react-query'

import {
  ACCOUNT_PREFERENCES_QUERY_KEY,
  patchAccountPreferences,
} from '../api/accountApi'
import { isTimesheetOnlyUser, isUserManagerOrAdmin } from '../domain/auth/authRoles'
import { useNotifyToast } from '../hooks/useNotifyToast'
import { useAuthStore } from '../store/authStore'
import { userFacingMessageFromUnknown } from '../utils/apiUserMessage'
import { clearGuidedTourSeenStepIds } from './guidedTourSeenStorage'
import { resolveGuidedTourSteps } from './steps'
import { useTourStore } from './tourStore'

/** Ручной повтор guided tour (аккаунт или кнопка «Обучение» в меню). */
export function useRestartGuidedTour() {
  const qc = useQueryClient()
  const user = useAuthStore((s) => s.user)
  const restartWithSteps = useTourStore((s) => s.restartWithSteps)
  const notify = useNotifyToast()

  const resetMut = useMutation({
    mutationFn: () => patchAccountPreferences({ guided_tour_completed: false }),
    onSuccess: (data) => {
      qc.setQueryData(ACCOUNT_PREFERENCES_QUERY_KEY, data)
      if (!user) return
      clearGuidedTourSeenStepIds(user.sub)
      const ctx = {
        isPortalAdmin: Boolean(user.is_portal_admin),
        isManagerOrAdmin: isUserManagerOrAdmin(user),
        isTimesheetOnly: isTimesheetOnlyUser(user),
      }
      restartWithSteps(resolveGuidedTourSteps(ctx))
    },
    onError: (error) => notify(userFacingMessageFromUnknown(error)),
  })

  return {
    restart: () => resetMut.mutate(),
    isPending: resetMut.isPending,
  }
}
