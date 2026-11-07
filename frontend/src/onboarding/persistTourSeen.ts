import {
  seenStepIdsAfterLinearComplete,
  seenStepIdsAfterLinearSkip,
} from '../domain/onboarding/guidedTourPages'
import type { GuidedTourStepDef } from '../domain/onboarding/guidedTour'
import {
  addGuidedTourSeenStepIds,
  writeGuidedTourSeenStepIds,
} from './guidedTourSeenStorage'

export function persistLinearTourSeen(args: {
  userSub: string | undefined
  steps: readonly GuidedTourStepDef[]
  stepIndex: number
  hasEnteredRunning: boolean
}): void {
  if (!args.userSub) return
  if (!args.hasEnteredRunning) {
    writeGuidedTourSeenStepIds(args.userSub, [])
    return
  }
  const atLast = args.steps.length > 0 && args.stepIndex >= args.steps.length - 1
  const ids = atLast
    ? seenStepIdsAfterLinearComplete(args.steps)
    : seenStepIdsAfterLinearSkip(args.steps, 'running', args.stepIndex)
  writeGuidedTourSeenStepIds(args.userSub, ids)
}

export function persistHintPageSeen(userSub: string | undefined, steps: readonly GuidedTourStepDef[]): void {
  if (!userSub) return
  addGuidedTourSeenStepIds(
    userSub,
    steps.map((item) => item.id),
  )
}
